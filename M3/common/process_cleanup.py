"""Stop only a recorded child tree, even when ROS launches new process groups."""
import os
from pathlib import Path
import signal
import subprocess
import time


def identity(pid):
    try:
        fields=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
        return None if fields[0]=='Z' else (int(fields[1]),fields[19])
    except (FileNotFoundError,ProcessLookupError,PermissionError): return None


def terminate_owned_tree(process,grace=6.):
    table={int(p.name):identity(int(p.name)) for p in Path('/proc').iterdir() if p.name.isdigit()}
    owned={process.pid}; changed=True
    while changed:
        children={pid for pid,value in table.items() if value and value[0] in owned}
        changed=not children.issubset(owned); owned.update(children)
    recorded={pid:table.get(pid) for pid in owned if table.get(pid)}
    def alive(pid):
        current=identity(pid)
        return current is not None and current[1]==recorded[pid][1]
    for sig,timeout in [(signal.SIGINT,grace),(signal.SIGTERM,3.),(signal.SIGKILL,2.)]:
        for pid in sorted(recorded,reverse=True):
            if alive(pid):
                try: os.kill(pid,sig)
                except ProcessLookupError: pass
        deadline=time.monotonic()+timeout
        while any(alive(pid) for pid in recorded) and time.monotonic()<deadline: time.sleep(.05)
    try: process.wait(timeout=2)
    except subprocess.TimeoutExpired: raise RuntimeError('Recorded child process did not exit: '+str(process.pid))
    remaining=[pid for pid in recorded if alive(pid)]
    if remaining: raise RuntimeError('Owned child processes survived cleanup: '+str(remaining))
