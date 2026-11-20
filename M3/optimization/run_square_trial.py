"""Own-process Gazebo experiment; archive settings, all runs and failures."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT=Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0,str(ROOT/'M3/common'))
from experiment_lock import acquire
experiment_lock=acquire()
p=argparse.ArgumentParser(); p.add_argument('--mode',choices=['feedback','timed'],default='feedback')
p.add_argument('--rear-axle-reference',choices=['true','false'],default='true')
p.add_argument('--laps',type=int,default=1); p.add_argument('--speed',type=float,default=.28); p.add_argument('--turn-speed',type=float,default=.18)
p.add_argument('--label',default='candidate'); p.add_argument('--domain',default='171'); p.add_argument('--port',default='11381')
p.add_argument('--gui',action='store_true'); p.add_argument('--seed',type=int,default=42)
a=p.parse_args()
out=ROOT/'M3/optimization/results'/(time.strftime('%Y%m%d_%H%M%S')+'_'+a.label); out.mkdir(parents=True)
env=dict(os.environ,ROS_DOMAIN_ID=a.domain,GAZEBO_MASTER_URI='http://127.0.0.1:'+a.port,GAZEBO_MODEL_DATABASE_URI='')
settings=dict(vars(a),source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),started=time.time())
(out/'settings.json').write_text(json.dumps(settings,indent=2))
(out/'controller.yaml').write_bytes((ROOT/'M3/M3-1/src/smart_car_description/config/ackermann_controllers.yaml').read_bytes())
with (out/'model.urdf').open('w') as model:
    subprocess.run(['xacro',str(ROOT/'M3/M3-1/src/smart_car_description/urdf/smart_car.urdf.xacro'),'rear_axle_reference:='+a.rear_axle_reference],stdout=model,check=True)
log=(out/'simulation.log').open('w')
proc=subprocess.Popen(['ros2','launch','smart_car_description','sim.launch.py','rear_axle_reference:='+a.rear_axle_reference,'physics_seed:='+str(a.seed)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
viewer=subprocess.Popen(['gzclient'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True) if a.gui else None
result=None
try:
    with (out/'driver.log').open('w') as driver:
        result=subprocess.run([str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M3/M3-1/scripts/square_driver.py'),'--mode',a.mode,'--laps',str(a.laps),'--speed',str(a.speed),'--turn-speed',str(a.turn_speed),'--out',str(out/'logs')],cwd=ROOT,env=env,stdout=driver,stderr=subprocess.STDOUT,timeout=1200*a.laps)
    settings['returncode']=result.returncode
    print((out/'driver.log').read_text()[-6000:],flush=True)
finally:
    if viewer and viewer.poll() is None:
        os.killpg(viewer.pid,signal.SIGTERM)
        try: viewer.wait(timeout=5)
        except subprocess.TimeoutExpired: os.killpg(viewer.pid,signal.SIGKILL); viewer.wait()
    if proc.poll() is None:
        os.killpg(proc.pid,signal.SIGINT)
        try: proc.wait(timeout=15)
        except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL); proc.wait()
    log.close(); settings['finished']=time.time(); (out/'settings.json').write_text(json.dumps(settings,indent=2))
    print('SQUARE_EXPERIMENT',out,flush=True)
if result is None or result.returncode: raise SystemExit(1)
if a.laps>=10:
    subprocess.run([str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M3/M3-1/scripts/analyze.py'),'--logs',str(out/'logs'),'--out',str(out)],check=True)
