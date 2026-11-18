import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(); p.add_argument('--runs',type=int,default=3); p.add_argument('--params'); p.add_argument('--label',default='static'); p.add_argument('--obstacle-at'); p.add_argument('--delay',default='3.0'); p.add_argument('--obstacle-size',default='.6'); p.add_argument('--domain-base',type=int,default=100); a=p.parse_args()
out=ROOT/'M3/M3-3/results'/(time.strftime('%Y%m%d_%H%M%S')+'_'+a.label); out.mkdir(parents=True); reports=[]
env=dict(os.environ,ROS_DOMAIN_ID='67',GAZEBO_MASTER_URI='http://127.0.0.1:11377',GAZEBO_MODEL_DATABASE_URI='',DISPLAY=':0')
for i in range(a.runs):
    env['ROS_DOMAIN_ID']=str(a.domain_base+i) # isolate clock resets and DDS histories between independent trials
    run=out/('run_%02d'%(i+1)); run.mkdir(); log=(run/'navigation.log').open('w')
    command=['ros2','launch',str(ROOT/'M3/M3-3/bringup.launch.py')]
    if a.params: command.append('params_file:='+str(Path(a.params).resolve()))
    proc=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    viewer=None
    if i==0 and a.label.startswith('dynamic'):
        viewer=subprocess.Popen([str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M3/M3-4/scripts/live_view.py'),'--out',str(run/'screenshots'),'--obstacle-at',a.obstacle_at or '8.0,1.6','--obstacle-size',a.obstacle_size],env=dict(env,QT_QPA_PLATFORM='offscreen'),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        command=[str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M3/M3-3/scripts/nav_trial.py'),'--out',str(run)]
        if a.obstacle_at: command+=['--obstacle-at',a.obstacle_at,'--delay',a.delay,'--obstacle-size',a.obstacle_size]
        result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=1800)
        (run/'trial.log').write_text(result.stdout+result.stderr); print(result.stdout+result.stderr,flush=True)
        if result.returncode: raise RuntimeError('Trial failed; see '+str(run))
        reports.append(json.loads((run/'result.json').read_text())); (out/'runs.json').write_text(json.dumps(reports,indent=2))
    finally:
        if viewer and viewer.poll() is None:
            os.killpg(viewer.pid,signal.SIGTERM)
            try: viewer.wait(timeout=5)
            except subprocess.TimeoutExpired: os.killpg(viewer.pid,signal.SIGKILL); viewer.wait()
        if proc.poll() is None: os.killpg(proc.pid,signal.SIGINT)
        try: proc.wait(timeout=15)
        except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL); proc.wait()
        log.close()
print('SUCCESS_RATE',sum(r['success'] for r in reports)/len(reports),flush=True)
