"""Stop an identified training leaf, allowing its own orchestration cleanup to run."""
import argparse
import os
from pathlib import Path
import signal
import psutil
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(); p.add_argument('kind',choices=['terminal','nav_trial','navstack','viewer']); a=p.parse_args()
suffix={'terminal':'M5/M5-2/host_side/dashboard.py','nav_trial':'M3/M3-3/scripts/nav_trial.py','navstack':'M3/M3-3/bringup.launch.py','viewer':'M3/M3-4/scripts/live_view.py'}[a.kind]
matches=[]
for process in psutil.process_iter(['pid','cmdline','cwd']):
    command=process.info['cmdline'] or []
    if process.pid==os.getpid() or len(command)<2: continue
    try:
        cwd=Path(process.info['cwd']).resolve()
        if cwd==ROOT and any(arg.endswith(suffix) for arg in command[1:]): matches.append(process)
    except (OSError,TypeError): pass
if len(matches)!=1: raise RuntimeError('Expected exactly one owned target, got '+str([(p.pid,p.cmdline()) for p in matches]))
print('Interrupting only owned job',matches[0].pid,suffix); matches[0].send_signal(signal.SIGINT)
if a.kind=='viewer':
    try: matches[0].wait(timeout=5)
    except psutil.TimeoutExpired: matches[0].kill(); matches[0].wait(timeout=5)
