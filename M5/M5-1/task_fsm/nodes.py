import threading
import time


class TaskNode:
    def __init__(self, name, params, ctx):
        self.name, self.params, self.ctx = name, params, ctx
        self.cancelled = threading.Event()

    def setup(self):
        pass

    def execute(self):
        raise NotImplementedError

    def cancel(self):
        self.cancelled.set()

    def teardown(self):
        pass

    def progress(self, value, **details):
        self.ctx.emit(self.name, 'RUNNING', progress=value, **details)

    def request(self, kind):
        return self.ctx.metadata['backend'].perform(kind, self)


class WaitForTrigger(TaskNode):
    def execute(self):
        result = self.request('trigger')
        return 'SUCCESS' if result.get('success') else 'FAILED'


class NavigateTo(TaskNode):
    def execute(self):
        params = self.params
        pose = self.ctx.data.get(params.get('pose_from_context', '')) if 'pose_from_context' in params else params.get('pose')
        if not isinstance(pose, (dict, list, tuple)):
            return 'FAILED'
        result = self.request('navigate')
        if self.cancelled.is_set():
            return 'FAILED'
        self.ctx.data['last_nav_result'] = result
        return 'SUCCESS' if result.get('success') else 'FAILED'


class DetectTarget(TaskNode):
    def execute(self):
        while self.ctx.checkpoint(self.cancelled):
            result = self.request('detect')
            if not result.get('success', True):
                return 'FAILED'
            for target in result.get('targets', []):
                if target.get('class') == self.params.get('target_class') and target.get('confidence', 0) >= self.params.get('min_confidence', 0.7):
                    self.ctx.data.update(target_pose=target.get('pose'), target_id=target.get('id'))
                    return 'SUCCESS'
            self.cancelled.wait(0.01)
        return 'FAILED'


class ExecuteGrasp(TaskNode):
    def execute(self):
        if not self.params.get('grasp_pose', self.ctx.data.get('target_pose')):
            return 'FAILED'
        result = self.request('grasp')
        if self.cancelled.is_set():
            return 'FAILED'
        self.ctx.data.update(grasp_result=result, object_pose=result.get('object_pose'))
        return 'SUCCESS' if result.get('success') else 'FAILED'


class SpeakTTS(TaskNode):
    def execute(self):
        if not isinstance(self.params.get('text'), str):
            return 'FAILED'
        return 'SUCCESS' if self.request('speak').get('success') else 'FAILED'


class MockBackend:
    """Explicit simulator for contracts; no simulated results are board benchmarks."""
    def __init__(self):
        self.calls = {}
        self.lock = threading.Lock()

    def perform(self, kind, node):
        with self.lock:
            index = self.calls.get(node.name, 0)
            self.calls[node.name] = index + 1
        started = time.monotonic()
        delay = float(node.params.get('mock_delay_s', 0.005))
        while time.monotonic()-started < delay:
            if not node.ctx.checkpoint(node.cancelled):
                return {'success': False, 'cancelled': True}
            node.cancelled.wait(min(0.005, delay))
        outcomes = node.params.get('mock_outcomes', ['SUCCESS'])
        success = outcomes[min(index, len(outcomes)-1)] == 'SUCCESS'
        if kind == 'trigger':
            while not node.params.get('auto_trigger', False) and not node.ctx.data.get('triggered', False):
                if not node.ctx.checkpoint(node.cancelled):
                    return {'success': False}
                node.cancelled.wait(0.01)
        node.progress(1.0)
        return {'success': success, 'mock': True,
                'targets': node.params.get('mock_targets', []),
                'object_pose': node.params.get('grasp_pose', node.ctx.data.get('target_pose'))}
