import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scheduler import Task, load_config, topological_order


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
