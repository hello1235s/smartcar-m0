"""Controlled single/batch navigation trials, exact snapshots, bounded cleanup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import time
import yaml

ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(); p.add_argument('--runs',type=int,default=1); p.add_argument('--label',default='candidate_static')
p.add_argument('--params',type=Path); p.add_argument('--obstacle-at'); p.add_argument('--obstacle-size',type=float,default=.6)
p.add_argument('--delay',type=float,default=3.); p.add_argument('--timeout',type=float,default=150.)
p.add_argument('--seed',type=int,default=100); p.add_argument('--domain',type=int,default=180); p.add_argument('--port',default='11382')
p.add_argument('--gui',action='store_true'); p.add_argument('--viewer',action='store_true')
a=p.parse_args()
if not 1<=a.runs<=30 or not 0<=a.domain<=232-a.runs+1: p.error('runs/domain outside supported ROS DDS range')
folder=ROOT/'M3/optimization/results'/(time.strftime('%Y%m%d_%H%M%S')+'_'+a.label); folder.mkdir(parents=True)
params=(a.params or ROOT/'M3/M3-3/config/nav2_params.yaml').resolve()
configuration=yaml.safe_load(params.read_text())
for key,name in [('default_nav_to_pose_bt_xml','car_navigation.xml'),('default_nav_through_poses_bt_xml','car_through_poses.xml')]:
    configuration['bt_navigator']['ros__parameters'][key]=str(ROOT/'M3/M3-3/config'/name)
actual=folder/'parameters_used.yaml'; actual.write_text(yaml.safe_dump(configuration,sort_keys=False))
snapshots=folder/'map_used'; snapshots.mkdir()
for name in ['map.yaml','map.pgm','map_manifest.json']:
    if (ROOT/'M3/M3-2/maps'/name).exists(): shutil.copy2(ROOT/'M3/M3-2/maps'/name,snapshots/name)
sources={}
for base in ['M3/common','M3/M3-1/src','M3/M3-3','M3/optimization','scripts']:
    for path in (ROOT/base).rglob('*'):
        if path.is_file() and path.suffix in ['.py','.xacro','.cpp','.xml','.world','.sh'] and not any(part in ['results','__pycache__','baseline'] for part in path.relative_to(ROOT).parts):
            sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
(folder/'source_hashes.json').write_text(json.dumps(sources,indent=2,sort_keys=True))
metadata=dict(label=a.label,runs_requested=a.runs,obstacle_at=a.obstacle_at,obstacle_size=a.obstacle_size,delay_s=a.delay,
              base_seed=a.seed,params_source=str(params),params_sha256=hashlib.sha256(actual.read_bytes()).hexdigest(),
              code_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              source_manifest_sha256=hashlib.sha256((folder/'source_hashes.json').read_bytes()).hexdigest(),
              map_sha256=hashlib.sha256((ROOT/'M3/M3-2/maps/map.pgm').read_bytes()).hexdigest(),
              independent_qualification=dict(position_m=.15,yaw_rad=.20,minimum_path_m=5.,geometric_overlap_limit_m=-.002))
(folder/'experiment.json').write_text(json.dumps(metadata,indent=2)); reports=[]
for i in range(a.runs):
    directory=folder/('run_%02d'%(i+1)); directory.mkdir()
    env=dict(os.environ,ROS_DOMAIN_ID=str(a.domain+i),GAZEBO_MASTER_URI='http://127.0.0.1:'+a.port,GAZEBO_MODEL_DATABASE_URI='')
    process=None; children=[]; log=(directory/'navigation.log').open('w')
    try:
        process=subprocess.Popen(['ros2','launch',str(ROOT/'M3/M3-3/bringup.launch.py'),'params_file:='+str(actual),'physics_seed:='+str(a.seed+i)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        if a.gui:
            children.append(subprocess.Popen(['gzclient'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True))
        if a.viewer:
            viewargs=[str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M3/M3-4/scripts/live_view.py'),'--out',str(directory/'screenshots'),'--obstacle-at',a.obstacle_at or '8.0,1.6','--obstacle-size',str(a.obstacle_size)]
            viewenv=dict(env)
            if not a.gui: viewenv['QT_QPA_PLATFORM']='offscreen'
            children.append(subprocess.Popen(viewargs,cwd=ROOT,env=viewenv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True))
        command=[str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M3/M3-3/scripts/nav_trial.py'),'--out',str(directory),'--timeout',str(a.timeout)]
        if a.obstacle_at: command+=['--obstacle-at',a.obstacle_at,'--delay',str(a.delay),'--obstacle-size',str(a.obstacle_size)]
        with (directory/'trial.log').open('w') as driver:
            completed=subprocess.run(command,cwd=ROOT,env=env,stdout=driver,stderr=subprocess.STDOUT,timeout=a.timeout*8+240)
        if (directory/'result.json').exists(): report=json.loads((directory/'result.json').read_text())
        else: report=dict(success=False,action_success=False,goal_accepted=False,failure_reason='trial_process_failed_before_report',returncode=completed.returncode)
        report.update(run=i+1,seed=a.seed+i,result_dir=str(directory.relative_to(ROOT)))
        reports.append(report); (folder/'runs.json').write_text(json.dumps(reports,indent=2))
        print(json.dumps(report),flush=True)
    finally:
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGTERM)
                try: child.wait(timeout=6)
                except subprocess.TimeoutExpired: os.killpg(child.pid,signal.SIGKILL); child.wait()
        if process and process.poll() is None:
            os.killpg(process.pid,signal.SIGINT)
            try: process.wait(timeout=18)
            except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL); process.wait()
        log.close()
metadata.update(completed=len(reports),successes=sum(r['success'] for r in reports),accepted=sum(r.get('goal_accepted',False) for r in reports))
(folder/'experiment.json').write_text(json.dumps(metadata,indent=2))
print('NAVIGATION_EXPERIMENT',folder,metadata['successes'],len(reports),flush=True)
