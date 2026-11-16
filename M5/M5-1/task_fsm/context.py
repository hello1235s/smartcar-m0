import threading
import time
from dataclasses import dataclass, field


@dataclass
class TaskContext:
    task_id: str = 'training'
    deadline: float = field(default_factory=lambda: time.monotonic() + 180)
    data: dict = field(default_factory=dict)
    retry_budget: int = 20
    degraded: bool = False
    metadata: dict = field(default_factory=dict)
    cancelled: threading.Event = field(default_factory=threading.Event, repr=False)
    gate: threading.Event = field(default_factory=threading.Event, repr=False)
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    active: set = field(default_factory=set, repr=False)
    events: list = field(default_factory=list)

    def __post_init__(self):
        self.gate.set()

    def emit(self, name, status, **details):
        event = {'ts_ns': time.time_ns(), 'task_id': self.task_id, 'name': name, 'status': status, **details}
        with self.lock:
            self.events.append(event)
        callback = self.metadata.get('on_event')
        if callback:
            callback(event)

    def pause(self):
        with self.lock:
            self.gate.clear()
            for node in tuple(self.active):
                node.cancel()
        self.emit('task', 'PAUSED')

    def resume(self):
        self.gate.set()
        self.emit('task', 'RESUMED')

    def abort(self):
        with self.lock:
            self.cancelled.set()
            self.gate.set()
            for node in tuple(self.active):
                node.cancel()
        self.emit('task', 'ABORTED')

    def skip(self):
        with self.lock:
            self.metadata['skip_current'] = True
            for node in tuple(self.active):
                node.cancel()

    def checkpoint(self, cancel):
        return not self.cancelled.is_set() and not cancel.is_set() and time.monotonic() < self.deadline
