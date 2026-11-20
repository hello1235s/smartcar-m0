"""Keep CPU-sensitive M3 experiment processes sequential on one host."""
import fcntl
from pathlib import Path


def acquire():
    stream=Path('/tmp/smartcar_m3_experiment.lock').open('a+')
    try: fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        stream.close()
        raise RuntimeError('Another M3 experiment is active; finish it before starting this one')
    active=[]
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit(): continue
        try:
            if (folder/'comm').read_text().strip()=='gzserver' and (folder/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':
                active.append(folder.name)
        except (FileNotFoundError,PermissionError,ProcessLookupError): pass
    if active:
        stream.close()
        raise RuntimeError('Existing Gazebo server must be closed before a fresh experiment: PIDs '+','.join(active))
    return stream  # Keep alive for the caller's entire process lifetime.
