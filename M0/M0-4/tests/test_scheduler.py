import json
import sys
import subprocess
import time
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scheduler import Task, TaskScheduler, load_config, topological_order


def config_file(tmp_path, tasks, **extra):
    path = tmp_path / 'tasks.yaml'
    path.write_text(yaml.safe_dump({'tasks': tasks, **extra}))
    return path


def item(name='A', dependencies=None, **extra):
    return {'name': name, 'duration': 0.01, 'success_rate': 1,
            'dependencies': dependencies or [], **extra}


def test_unordered_diamond_graph(tmp_path):
    path = config_file(tmp_path, [item('D', ['B', 'C']), item('C', ['A']), item('A'), item('B', ['A'])])
    tasks, timeout = load_config(path)
    order = [t.name for t in topological_order(tasks)]
    assert order[0] == 'A' and order[-1] == 'D'
    assert set(order[1:3]) == {'B', 'C'} and timeout == 15


@pytest.mark.parametrize('tasks', [[], [item(), item()], [item('A', ['missing'])],
    [item('A', ['A'])], [item('A', ['B']), item('B', ['A'])],
    [item('A', ['B', 'B']), item('B')], [item(name='')], [None],
    [item(dependencies='B')], [item(duration=-1)], [item(duration=True)],
    [item(duration=float('nan'))], [item(success_rate=1.1)],
    [item(success_rate=-0.1)], [item(success_rate='0.5')]])
def test_invalid_graph_and_fields(tmp_path, tasks):
    with pytest.raises(ValueError):
        load_config(config_file(tmp_path, tasks))


@pytest.mark.parametrize('timeout', [0, -1, True, '15', float('inf')])
def test_invalid_timeout(tmp_path, timeout):
    with pytest.raises(ValueError):
        load_config(config_file(tmp_path, [item()], timeout=timeout))


def test_yaml_json_equivalent():
    root = Path(__file__).resolve().parents[1]
    assert load_config(root / 'tasks_demo.yaml') == load_config(root / 'tasks_demo.json')


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds

    def wall(self):
        return self.now + 1700000000


def simulate(tasks, timeout=15, seed=42, rng=None):
    clock = FakeClock()
    logs = []
    scheduler = TaskScheduler(tasks, timeout, seed, clock=clock.monotonic,
        sleep=clock.sleep, wall_clock=clock.wall, rng=rng,
        logger=lambda status, message: logs.append((status, message)))
    return scheduler.run(), logs


def test_failure_skips_transitive_dependents_but_runs_independent_tasks():
    tasks = [Task('A', 0.2, 0, ()), Task('B', 0.1, 1, ('A',)),
             Task('C', 0.1, 1, ('B',)), Task('Independent', 0.1, 1, ())]
    report, logs = simulate(tasks)
    rows = {t['name']: t for t in report['tasks']}
    assert rows['A']['attempts'] == 3 and rows['A']['status'] == 'SKIPPED'
    assert rows['B']['status'] == rows['C']['status'] == 'SKIPPED'
    assert rows['B']['attempts'] == rows['C']['attempts'] == 0
    assert rows['Independent']['status'] == 'SUCCESS'
    assert report['total_duration'] == pytest.approx(0.7)
    assert [status for status, _ in logs].count('RETRY') == 2


def test_retry_can_succeed_on_third_attempt():
    class Sequence:
        def __init__(self):
            self.values = iter([0.9, 0.8, 0.1])
        def random(self):
            return next(self.values)
    report, _ = simulate([Task('A', 0.1, 0.5, ())], rng=Sequence())
    assert report['tasks'][0]['status'] == 'SUCCESS'
    assert report['tasks'][0]['attempts'] == 3
    assert report['tasks'][0]['duration'] == pytest.approx(0.3)


def test_timeout_interrupts_long_sleep_and_reports_all_tasks():
    report, _ = simulate([Task('Long', 20, 1, ()), Task('Later', 0, 1, ('Long',))], timeout=0.25)
    assert report['timeout'] and report['total_duration'] == pytest.approx(0.25)
    assert [t['status'] for t in report['tasks']] == ['TIMEOUT', 'TIMEOUT']
    assert report['tasks'][0]['attempts'] == 1
    assert report['tasks'][1]['attempts'] == 0
    assert report['tasks'][1]['started_at'] is None


def test_timeout_during_retries_keeps_completed_success():
    report, _ = simulate([Task('Ready', 0.1, 1, ()), Task('Fail', 0.3, 0, ('Ready',)),
                          Task('Later', 0.1, 1, ('Fail',))], timeout=0.6)
    assert report['timeout']
    assert report['tasks'][0]['status'] == 'SUCCESS'
    assert report['tasks'][1]['status'] == report['tasks'][2]['status'] == 'TIMEOUT'
    assert report['tasks'][1]['attempts'] == 2


def test_zero_duration_and_dependency_diamond():
    tasks = [Task('D', 0, 1, ('B', 'C')), Task('B', 0, 1, ('A',)),
             Task('C', 0, 1, ('A',)), Task('A', 0, 1, ())]
    report, _ = simulate(tasks)
    assert not report['timeout']
    assert report['execution_order'][0] == 'A' and report['execution_order'][-1] == 'D'
    assert all(t['status'] == 'SUCCESS' for t in report['tasks'])
    assert [t['name'] for t in report['tasks']] == ['D', 'B', 'C', 'A']


def test_seed_reproduces_outcomes():
    tasks = [Task('A', 0, 0.5, ()), Task('B', 0, 0.3, ('A',))]
    first, _ = simulate(tasks, seed=10)
    second, _ = simulate(tasks, seed=10)
    assert first == second


def cli(tmp_path, config, *options):
    script = Path(__file__).resolve().parents[1] / 'scheduler.py'
    return subprocess.run([sys.executable, str(script), '--config', str(config), *options],
                          cwd=tmp_path, capture_output=True, text=True, timeout=4)


def test_real_cli_interrupts_20_second_task(tmp_path):
    path = config_file(tmp_path, [item(duration=20), item('B', ['A'])])
    start = time.monotonic()
    run = cli(tmp_path, path, '--timeout', '0.15', '--seed', '42')
    assert run.returncode == 124 and time.monotonic() - start < 2
    report = json.loads((tmp_path / 'report.json').read_text())
    assert report['timeout'] and len(report['tasks']) == 2
    assert 0.14 <= report['total_duration'] < 1
    assert 'TIMEOUT' in run.stdout and '\x1b[' not in run.stdout


def test_cli_yaml_report_and_forced_color(tmp_path):
    run = cli(tmp_path, config_file(tmp_path, [item()]), '--report', 'result.yaml', '--color', 'always')
    assert run.returncode == 0 and '\x1b[32m' in run.stdout
    report = yaml.safe_load((tmp_path / 'result.yaml').read_text())
    assert not report['timeout'] and report['tasks'][0]['status'] == 'SUCCESS'


def test_cli_exhausted_retries_exit_one(tmp_path):
    run = cli(tmp_path, config_file(tmp_path, [item(duration=0, success_rate=0)]))
    assert run.returncode == 1
    report = json.loads((tmp_path / 'report.json').read_text())
    assert report['tasks'][0]['attempts'] == 3 and report['tasks'][0]['status'] == 'SKIPPED'


@pytest.mark.parametrize('content', ['', '[]', 'tasks: [', 'tasks: []'])
def test_cli_bad_configuration_no_traceback(tmp_path, content):
    path = tmp_path / 'bad.yaml'
    path.write_text(content)
    run = cli(tmp_path, path)
    assert run.returncode == 2 and 'Traceback' not in run.stderr
    assert not (tmp_path / 'report.json').exists()


@pytest.mark.parametrize('extra', [['--timeout', '0'], ['--timeout', 'nan'],
    ['--timeout', 'inf'], ['--report', 'missing/f.json'], ['--report', 'r.txt']])
def test_cli_bad_options(tmp_path, extra):
    run = cli(tmp_path, config_file(tmp_path, [item()]), *extra)
    assert run.returncode == 2 and 'Traceback' not in run.stderr


def test_does_not_overwrite_input_configuration(tmp_path):
    path = config_file(tmp_path, [item()])
    before = path.read_text()
    run = cli(tmp_path, path, '--report', str(path))
    assert run.returncode == 2 and path.read_text() == before
