import concurrent.futures
import threading
import time
import yaml
from .registry import REGISTRY


class Engine:
    def __init__(self, document, ctx):
        if isinstance(document, str):
            try:
                with open(document, encoding='utf-8') as source:
                    document = yaml.safe_load(source)
            except yaml.YAMLError as error:
                mark = getattr(error, 'problem_mark', None)
                raise ValueError('Invalid YAML at line %s: %s' % (mark.line+1 if mark else '?', error)) from None
        if not isinstance(document, dict) or not isinstance(document.get('tasks'), list):
            raise ValueError('YAML requires a tasks list')
        self.tasks, self.ctx = document['tasks'], ctx
        self.lookup, self.visits, self.steps = {}, {}, []
        def validate(specs):
            for spec in specs:
                if not isinstance(spec, dict) or not isinstance(spec.get('name'), str):
                    raise ValueError('Every task needs a unique string name')
                name = spec['name']
                if name in self.lookup:
                    raise ValueError('Duplicate task: '+name)
                self.lookup[name] = spec
                if 'parallel' in spec:
                    branch = spec['parallel']
                    if branch.get('fail_policy', 'any_fail') not in ('any_fail', 'all_must_succeed'):
                        raise ValueError('Unknown parallel fail_policy in '+name)
                    if not isinstance(branch.get('branches'), list) or not branch['branches']:
                        raise ValueError('Parallel needs branches: '+name)
                    validate(branch['branches'])
                elif spec.get('type') not in REGISTRY:
                    raise ValueError('Unknown type %s; available: %s' % (spec.get('type'), ', '.join(REGISTRY)))
                if float(spec.get('timeout', 30)) <= 0 or int(spec.get('retry', 0)) < 0:
                    raise ValueError('timeout must be positive; retry must be nonnegative: '+name)
                if spec.get('on_fail', 'abort') not in ('skip', 'abort'):
                    raise ValueError('on_fail must be skip or abort: '+name)
        validate(self.tasks)
        for spec in self.lookup.values():
            if spec.get('fallback') and spec['fallback'] not in self.lookup:
                raise ValueError('Unknown fallback: '+spec['fallback'])

    def stopped(self):
        return self.ctx.cancelled.is_set() or time.monotonic() >= self.ctx.deadline

    def wait_gate(self):
        while not self.ctx.gate.wait(0.01):
            if self.stopped():
                return False
        return not self.stopped()

    def leaf(self, spec, deadline, scopes=()):
        node = REGISTRY[spec['type']](spec['name'], spec, self.ctx)
        result = {'status': 'FAILED'}
        def execute():
            try:
                node.setup()
                result['status'] = node.execute()
                if result['status'] not in ('SUCCESS', 'FAILED', 'SKIPPED'):
                    result.update(status='FAILED', error='invalid node result')
            except Exception as error:
                result.update(status='FAILED', error=str(error))
            finally:
                try:
                    node.teardown()
                except Exception as error:
                    result.update(status='FAILED', error=str(error))
        with self.ctx.lock:
            self.ctx.active.add(node)
        worker = threading.Thread(target=execute, name=spec['name'])
        worker.start()
        while worker.is_alive() and not self.stopped() and time.monotonic() < deadline and self.ctx.gate.is_set() and not any(event.is_set() for event in scopes):
            worker.join(0.01)
        interrupted = worker.is_alive()
        if interrupted:
            node.cancel()
            worker.join(0.5)
        with self.ctx.lock:
            self.ctx.active.discard(node)
        if worker.is_alive():
            raise RuntimeError('Node did not honor cancel(): '+spec['name'])
        if not self.ctx.gate.is_set() and self.wait_gate():
            return self.leaf(spec, min(self.ctx.deadline, time.monotonic()+float(spec.get('timeout', 30))), scopes)
        if self.ctx.metadata.pop('skip_current', False):
            return 'SKIPPED', 'operator skip'
        return ('FAILED', 'timeout/cancel') if interrupted else (result['status'], result.get('error'))

    def parallel(self, spec, deadline, scopes=()):
        branches = spec['parallel']['branches']
        statuses = []
        group_cancel = threading.Event()
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(branches)) as executor:
            futures = [executor.submit(self.run_step, branch, deadline, True, scopes+(group_cancel,)) for branch in branches]
            for future in concurrent.futures.as_completed(futures):
                status = future.result()
                statuses.append(status)
                if status == 'FAILED' and spec['parallel'].get('fail_policy', 'any_fail') == 'any_fail':
                    group_cancel.set()
                    with self.ctx.lock:
                        for node in tuple(self.ctx.active):
                            node.cancel()
        return ('FAILED' if 'FAILED' in statuses else 'SUCCESS'), None

    def run_step(self, spec, parent_deadline, branch=False, scopes=()):
        name, started = spec['name'], time.monotonic()
        with self.ctx.lock:
            self.visits[name] = self.visits.get(name, 0)+1
            visits = self.visits[name]
        if visits > int(self.ctx.metadata.get('max_visits', 3)):
            self.ctx.emit(name, 'FAILED', reason='fallback visit limit')
            return 'FAILED'
        self.ctx.emit(name, 'IDLE')
        status, error, retries = 'FAILED', None, 0
        for attempt in range(int(spec.get('retry', 0))+1):
            if not self.wait_gate() or any(event.is_set() for event in scopes):
                break
            if attempt:
                with self.ctx.lock:
                    if self.ctx.retry_budget <= 0:
                        break
                    self.ctx.retry_budget -= 1
                retries += 1
                self.ctx.emit(name, 'RETRYING', retry=retries)
                if self.ctx.cancelled.wait(float(spec.get('retry_interval', 0))):
                    break
            self.ctx.emit(name, 'RUNNING', attempt=attempt)
            deadline = min(parent_deadline, self.ctx.deadline, time.monotonic()+float(spec.get('timeout', 30)))
            status, error = self.parallel(spec, deadline, scopes) if 'parallel' in spec else self.leaf(spec, deadline, scopes)
            if status in ('SUCCESS', 'SKIPPED') or self.stopped():
                break
        degraded = status == 'FAILED' and bool(spec.get('fallback') or spec.get('on_fail') == 'skip')
        if degraded:
            self.ctx.degraded = True
        if branch and status == 'FAILED' and spec.get('fallback') and visits <= 3:
            status = self.run_step(self.lookup[spec['fallback']], parent_deadline, True, scopes)
            status = 'SKIPPED' if status == 'SUCCESS' else status
        elif status == 'FAILED' and not spec.get('fallback') and spec.get('on_fail') == 'skip':
            status = 'SKIPPED'
        entry = {'name': name, 'status': status, 'elapsed_s': time.monotonic()-started, 'retries': retries, 'degraded': degraded, 'error': error}
        with self.ctx.lock:
            self.steps.append(entry)
        self.ctx.emit(name, status, **{k:v for k,v in entry.items() if k not in ('name', 'status')})
        return status

    def run(self):
        started, index, status = time.monotonic(), 0, 'SUCCESS'
        indices = {spec['name']: i for i, spec in enumerate(self.tasks)}
        while index < len(self.tasks) and not self.stopped():
            spec = self.tasks[index]
            status = self.run_step(spec, self.ctx.deadline)
            if status == 'FAILED':
                fallback = spec.get('fallback')
                if fallback in indices and self.visits.get(spec['name'], 0) <= self.ctx.metadata.get('max_visits', 3):
                    index = indices[fallback]
                    continue
                break
            index += 1
        result = 'ABORTED' if self.ctx.cancelled.is_set() else 'TIMEOUT' if time.monotonic() >= self.ctx.deadline else 'FAILED' if status == 'FAILED' else 'SUCCESS'
        return {'task_id': self.ctx.task_id, 'result': result, 'total_elapsed_s': time.monotonic()-started,
                'steps': self.steps, 'final_context': dict(self.ctx.data), 'degraded': self.ctx.degraded,
                'backend': self.ctx.metadata.get('backend_name', 'unknown'), 'retry_budget_remaining': self.ctx.retry_budget}
