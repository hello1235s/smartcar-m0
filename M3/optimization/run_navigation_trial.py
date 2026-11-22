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
import sys
sys.path.insert(0,str(ROOT/'M3/common'))
from experiment_lock import acquire
from process_cleanup import terminate_owned_tree
from navigation_transport import configure,inspect_native_tf2
transport=configure(ROOT)
experiment_lock=acquire()
p=argparse.ArgumentParser(); p.add_argument('--runs',type=int,default=1); p.add_argument('--label',default='candidate_static')
p.add_argument('--params',type=Path); p.add_argument('--obstacle-at'); p.add_argument('--obstacle-size',type=float,default=.6)
p.add_argument('--delay',type=float,default=3.); p.add_argument('--timeout',type=float,default=150.)
p.add_argument('--seed',type=int,default=100); p.add_argument('--domain',type=int,default=180); p.add_argument('--port',default='11382')
p.add_argument('--goal',default='10,4,1.5707963267948966')
p.add_argument('--goal-source',choices=['coordinates','rviz'],default='coordinates')
p.add_argument('--goal-wait-timeout',type=float,default=180.)
p.add_argument('--injection-reference',choices=['accepted','motion'],default='accepted')
p.add_argument('--rviz',action='store_true')
p.add_argument('--record-view',action='store_true')
p.add_argument('--gui',action='store_true'); p.add_argument('--viewer',action='store_true')
p.add_argument('--hold-after',type=float,default=0.,help='GUI-only presentation pause after the saved result; excluded from measurements')
a=p.parse_args()
if not 1<=a.runs<=30 or not 0<=a.domain<=232-a.runs+1: p.error('runs/domain outside supported ROS DDS range')
if not 0<=a.hold_after<=60: p.error('hold-after must be between0 and60 seconds')
folder=ROOT/'M3/optimization/results'/(time.strftime('%Y%m%d_%H%M%S')+'_'+a.label); folder.mkdir(parents=True)
params=(a.params or ROOT/'M3/M3-3/config/nav2_params.yaml').resolve()
configuration=yaml.safe_load(params.read_text())
for key,name in [('default_nav_to_pose_bt_xml','car_navigation.xml'),('default_nav_through_poses_bt_xml','car_through_poses.xml')]:
    configuration['bt_navigator']['ros__parameters'][key]=str(ROOT/'M3/M3-3/config'/name)
actual=folder/'parameters_used.yaml'; actual.write_text(yaml.safe_dump(configuration,sort_keys=False))
snapshots=folder/'map_used'; snapshots.mkdir()
for name in ['map.yaml','map.pgm','map_manifest.json']:
    if (ROOT/'M3/M3-2/maps'/name).exists(): shutil.copy2(ROOT/'M3/M3-2/maps'/name,snapshots/name)
shutil.copy2(ROOT/'M3/M3-1/src/smart_car_description/config/ackermann_controllers.yaml',folder/'controller_used.yaml')
with (folder/'model_used.urdf').open('w') as model:
    subprocess.run(['xacro',str(ROOT/'M3/M3-1/src/smart_car_description/urdf/smart_car.urdf.xacro'),'rear_axle_reference:=true'],stdout=model,check=True)
sources={}
for base in ['M3/common','M3/M3-1/src','M3/M3-2/worlds','M3/M3-2/config','M3/M3-3','M3/M3-4','M3/optimization','scripts']:
    for path in (ROOT/base).rglob('*'):
        if path.is_file() and (path.suffix in ['.py','.xacro','.cpp','.xml','.world','.sh','.hpp','.h','.yaml'] or path.name=='CMakeLists.txt') and not any(part in ['results','__pycache__','baseline'] for part in path.relative_to(ROOT).parts):
            sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
(folder/'source_hashes.json').write_text(json.dumps(sources,indent=2,sort_keys=True))
plugin=ROOT/'install_ros/smartcar_nav_checks/lib/libvalid_pose_goal_checker.so'
plugin_sha256=hashlib.sha256(plugin.read_bytes()).hexdigest() if plugin.exists() else None
controller_library=ROOT/'install_ros/smartcar_nav_checks/lib/libackermann_rpp.so'
controller_sha256=hashlib.sha256(controller_library.read_bytes()).hexdigest() if controller_library.exists() else None
versions=subprocess.run(['dpkg-query','-W','ros-humble-navigation2','ros-humble-nav2-controller','ros-humble-nav2-map-server','ros-humble-slam-toolbox','ros-humble-fastrtps','ros-humble-ackermann-steering-controller','ros-humble-tf2','ros-humble-tf2-ros','gazebo'],capture_output=True,text=True)
(folder/'runtime_versions.txt').write_text(versions.stdout+versions.stderr)
for name in ['packages.txt','packages.sha256']:
    shutil.copy2(ROOT/'vendor/m3-dds'/name,folder/('dds_'+name))
metadata=dict(label=a.label,runs_requested=a.runs,obstacle_at=a.obstacle_at,obstacle_size=a.obstacle_size,delay_s=a.delay,
              injection_reference=a.injection_reference,goal_source=a.goal_source,rviz_enabled=a.rviz,
              gui=a.gui,live_view=a.viewer,presentation_hold_wall_s=a.hold_after if a.gui else 0.,
              base_seed=a.seed,goal_map=a.goal,params_source=str(params),params_sha256=hashlib.sha256(actual.read_bytes()).hexdigest(),
              code_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              source_manifest_sha256=hashlib.sha256((folder/'source_hashes.json').read_bytes()).hexdigest(),
              goal_checker_library_sha256=plugin_sha256,**transport,
              ackermann_controller_library_sha256=controller_sha256,
              map_sha256=hashlib.sha256((ROOT/'M3/M3-2/maps/map.pgm').read_bytes()).hexdigest(),
              map_yaml_sha256=hashlib.sha256((ROOT/'M3/M3-2/maps/map.yaml').read_bytes()).hexdigest(),
              independent_qualification=dict(position_m=.15,yaw_rad=.20,minimum_path_m=5.,geometric_overlap_limit_m=-.002))
(folder/'experiment.json').write_text(json.dumps(metadata,indent=2)); reports=[]
for i in range(a.runs):
    directory=folder/('run_%02d'%(i+1)); directory.mkdir()
    env=dict(os.environ,ROS_DOMAIN_ID=str(a.domain+i),GAZEBO_MASTER_URI='http://127.0.0.1:'+a.port,GAZEBO_MODEL_DATABASE_URI='',FASTDDS_BUILTIN_TRANSPORTS='UDPv4')
    process=None; children=[]; log=(directory/'navigation.log').open('w')
    try:
        process=subprocess.Popen(['ros2','launch',str(ROOT/'M3/M3-3/bringup.launch.py'),'params_file:='+str(actual),'physics_seed:='+str(a.seed+i)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        if a.gui:
            children.append(subprocess.Popen(['gzclient'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True))
        if a.rviz:
            children.append(subprocess.Popen(['ros2','run','smartcar_nav_checks','rviz_showcase','--config',str(ROOT/'M3/M3-3/config/exam_navigation.rviz'),
                '--out',str(directory/'rviz'),
                '--ros-args','-p','use_sim_time:=true'],cwd=ROOT,env=dict(env,LIBGL_ALWAYS_SOFTWARE='1'),stdout=log,stderr=subprocess.STDOUT,start_new_session=True))
        if a.viewer:
            viewargs=[str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M3/M3-4/scripts/live_view.py'),'--out',str(directory/'screenshots'),'--obstacle-at',a.obstacle_at or '8.0,1.6','--obstacle-size',str(a.obstacle_size)]
            viewenv=dict(env)
            if a.record_view:viewargs.append('--record')
            if not a.gui: viewenv['QT_QPA_PLATFORM']='offscreen'
            children.append(subprocess.Popen(viewargs,cwd=ROOT,env=viewenv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True))
        command=[str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M3/M3-3/scripts/nav_trial.py'),'--out',str(directory),'--timeout',str(a.timeout),'--goal',a.goal]
        command+=['--goal-source',a.goal_source,'--goal-wait-timeout',str(a.goal_wait_timeout),'--injection-reference',a.injection_reference]
        if a.obstacle_at: command+=['--obstacle-at',a.obstacle_at,'--delay',str(a.delay),'--obstacle-size',str(a.obstacle_size)]
        with (directory/'trial.log').open('w') as driver:
            completed=subprocess.run(command,cwd=ROOT,env=env,stdout=driver,stderr=subprocess.STDOUT,timeout=a.timeout*8+240)
        if (directory/'result.json').exists(): report=json.loads((directory/'result.json').read_text())
        else: report=dict(success=False,action_success=False,goal_accepted=False,failure_reason='trial_process_failed_before_report',returncode=completed.returncode)
        report.update(run=i+1,seed=a.seed+i,result_dir=str(directory.relative_to(ROOT)))
        native_runtime=inspect_native_tf2(process.pid,ROOT)
        (directory/'native_runtime.json').write_text(json.dumps(native_runtime,indent=2))
        reports.append(report); (folder/'runs.json').write_text(json.dumps(reports,indent=2))
        metadata.update(completed=len(reports),successes=sum(r['success'] for r in reports),accepted=sum(r.get('goal_accepted',False) for r in reports),state='running')
        if not report.get('goal_accepted') or completed.returncode or native_runtime['status']!='PASS':
            metadata['state']='infrastructure_failure'
        (folder/'experiment.json').write_text(json.dumps(metadata,indent=2))
        print(json.dumps(report),flush=True)
        if metadata['state']=='infrastructure_failure':
            raise RuntimeError('Trial infrastructure failed; retained attempt, stopping without replacement: '+str(directory))
        if a.gui and a.hold_after and i==a.runs-1:
            print('GUI_RESULT_SAVED; presentation pause outside measured interval',a.hold_after,flush=True)
            time.sleep(a.hold_after)
    finally:
        for child in children: terminate_owned_tree(child)
        if process: terminate_owned_tree(process)
        log.close()
metadata.update(completed=len(reports),successes=sum(r['success'] for r in reports),accepted=sum(r.get('goal_accepted',False) for r in reports),state='complete')
(folder/'experiment.json').write_text(json.dumps(metadata,indent=2))
print('NAVIGATION_EXPERIMENT',folder,metadata['successes'],len(reports),flush=True)
