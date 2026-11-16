import threading
import time
from pathlib import Path
import pytest
from task_fsm import Engine, TaskContext
from task_fsm.nodes import MockBackend
from task_fsm.registry import REGISTRY


PARAMS = {
    'WaitForTrigger': {'auto_trigger': True},
    'NavigateTo': {'pose': {'x': 1, 'y': 0, 'yaw': 0}},
    'DetectTarget': {'target_class': 'qrcode', 'mock_targets': [{'class': 'qrcode', 'confidence': 0.9, 'id': 'qr1', 'pose': {'x': 1}}]},
    'ExecuteGrasp': {'grasp_pose': {'x': 1}, 'grasp_type': 'top_down'},
    'SpeakTTS': {'text': '开始'},
}


def context(seconds=3):
    return TaskContext(deadline=time.monotonic()+seconds, metadata={'backend': MockBackend(), 'backend_name': 'mock'})


def document(kind, **changes):
    return {'tasks': [{'name': 'subject', 'type': kind, 'timeout': 0.2, **PARAMS[kind], **changes}]}


@pytest.mark.parametrize('kind', PARAMS)
def test_each_node_success(kind):
    report = Engine(document(kind), context()).run()
    assert report['result'] == 'SUCCESS'
    assert report['steps'][0]['status'] == 'SUCCESS'


@pytest.mark.parametrize('kind', PARAMS)
def test_each_node_timeout(kind):
    started = time.monotonic()
    report = Engine(document(kind, timeout=0.02, mock_delay_s=0.2), context()).run()
    assert report['result'] == 'FAILED'
    assert time.monotonic()-started < 0.2


@pytest.mark.parametrize('kind', PARAMS)
def test_each_node_retry_after_failure(kind):
    report = Engine(document(kind, retry=1, mock_outcomes=['FAILED', 'SUCCESS']), context()).run()
    assert report['result'] == 'SUCCESS'
    assert report['steps'][0]['retries'] == 1


@pytest.mark.parametrize('kind', PARAMS)
def test_each_node_cancel(kind):
    node = REGISTRY[kind]('subject', {**PARAMS[kind], 'mock_delay_s': 0.5}, context())
    output = []
    worker = threading.Thread(target=lambda: output.append(node.execute()))
    worker.start()
    time.sleep(0.02)
    node.cancel()
    worker.join(0.3)
    assert not worker.is_alive()
    assert output == ['FAILED']


def test_fallback_and_cycle_are_bounded():
    doc = {'tasks': [
        {'name': 'a', 'type': 'SpeakTTS', 'text': 'a', 'mock_outcomes': ['FAILED'], 'fallback': 'b'},
        {'name': 'b', 'type': 'SpeakTTS', 'text': 'b', 'mock_outcomes': ['FAILED'], 'fallback': 'a'}]}
    report = Engine(doc, context()).run()
    assert report['result'] == 'FAILED' and report['degraded']
    assert len(report['steps']) <= 6


def test_timeout_degrades_to_skip():
    report = Engine(document('SpeakTTS', mock_delay_s=0.2, timeout=0.01, on_fail='skip'), context()).run()
    assert report['result'] == 'SUCCESS' and report['steps'][0]['status'] == 'SKIPPED'


def test_parallel_any_failure_cancels_long_sibling():
    started = time.monotonic()
    doc = {'tasks': [{'name': 'both', 'parallel': {'fail_policy': 'any_fail', 'branches': [
        {'name': 'bad', 'type': 'SpeakTTS', 'text': 'bad', 'mock_outcomes': ['FAILED']},
        {'name': 'slow', 'type': 'SpeakTTS', 'text': 'slow', 'mock_delay_s': 2}]}}]}
    report = Engine(doc, context()).run()
    assert report['result'] == 'FAILED'
    assert time.monotonic()-started < 0.5


def test_parallel_all_collects_success():
    doc = {'tasks': [{'name': 'both', 'parallel': {'fail_policy': 'all_must_succeed', 'branches': [
        {'name': 'one', 'type': 'SpeakTTS', 'text': 'one'},
        {'name': 'two', 'type': 'SpeakTTS', 'text': 'two'}]}}]}
    assert Engine(doc, context()).run()['result'] == 'SUCCESS'


def test_task_deadline_distinguished_from_step_timeout():
    assert Engine(document('SpeakTTS', mock_delay_s=1, timeout=2), context(0.03)).run()['result'] == 'TIMEOUT'


def test_abort_is_not_failed_or_timeout():
    ctx = context()
    timer = threading.Timer(0.02, ctx.abort)
    timer.start()
    report = Engine(document('SpeakTTS', mock_delay_s=1), ctx).run()
    timer.join()
    assert report['result'] == 'ABORTED'


def test_pause_resume_does_not_consume_retry_budget():
    ctx = context()
    engine = Engine(document('SpeakTTS', mock_delay_s=0.1), ctx)
    output = []
    worker = threading.Thread(target=lambda: output.append(engine.run()))
    worker.start()
    time.sleep(0.02)
    ctx.pause()
    time.sleep(0.04)
    assert worker.is_alive()
    ctx.resume()
    worker.join(1)
    assert output[0]['result'] == 'SUCCESS' and ctx.retry_budget == 20


def test_unknown_type_reports_available_types():
    with pytest.raises(ValueError, match='available:'):
        Engine({'tasks': [{'name': 'a', 'type': 'unknown'}]}, context())


def test_bad_yaml_has_line_number(tmp_path):
    path = tmp_path/'broken.yaml'
    path.write_text('tasks: [a,')
    with pytest.raises(ValueError, match='line'):
        Engine(str(path), context())


def test_core_under_200_lines():
    core = Path(__file__).resolve().parents[1]/'task_fsm/core.py'
    assert len(core.read_text().splitlines()) < 200
