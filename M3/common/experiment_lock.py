"""Keep CPU-sensitive M3 experiment processes sequential on one host."""
import fcntl
from pathlib import Path


def acquire():
    stream=Path('/tmp/smartcar_m3_experiment.lock').open('a+')
    try: fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        stream.close()
        raise RuntimeError('Another M3 experiment is active; finish it before starting this one')
    return stream  # Keep alive for the caller's entire process lifetime.
