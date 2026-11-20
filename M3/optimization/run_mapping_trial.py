"""Rebuild and qualify actual SLAM output before promoting a navigation map."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

ROOT=Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0,str(ROOT/'M3/common'))
from experiment_lock import acquire
experiment_lock=acquire()
p=argparse.ArgumentParser(); p.add_argument('--seed',type=int,default=43); p.add_argument('--label',default='qualified_mapping')
p.add_argument('--timeout',type=float,default=900.); p.add_argument('--promote',action=argparse.BooleanOptionalAction,default=True)
a=p.parse_args(); os.environ['ROS_DOMAIN_ID']='165'
env=dict(os.environ,ROS_DOMAIN_ID='165',GAZEBO_MASTER_URI='http://127.0.0.1:11383',GAZEBO_MODEL_DATABASE_URI='')
out=ROOT/'M3/M3-2/results'/(time.strftime('%Y%m%d_%H%M%S')+'_'+a.label); out.mkdir(parents=True)
settings=dict(seed=a.seed,label=a.label,promote_requested=a.promote,started=time.time(),truth_input_to_slam=False,
              code_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
(out/'settings.json').write_text(json.dumps(settings,indent=2))
shutil.copy2(ROOT/'M3/M3-2/config/slam_params.yaml',out/'slam_params_used.yaml')
tool=ROOT/'tmp/posegraph_tool'
with (out/'graph_tool_build.log').open('w') as log:
    subprocess.run(['cmake','-S',str(ROOT/'M3/M3-2/scripts'),'-B',str(tool)],stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run(['cmake','--build',str(tool)],stdout=log,stderr=subprocess.STDOUT,check=True)
processes=[]; streams=[]; qualification=None
def start(command,name):
    log=(out/(name+'.log')).open('w'); streams.append(log)
    process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    processes.append(process); return process
try:
    start(['ros2','launch','smart_car_description','sim.launch.py','world:='+str(ROOT/'M3/M3-2/worlds/scene.world'),'x:=1.0','y:=1.0','physics_seed:='+str(a.seed)],'simulation')
    start(['ros2','run','slam_toolbox','async_slam_toolbox_node','--ros-args','--params-file',str(out/'slam_params_used.yaml')],'slam')
    start(['ros2','bag','record','-o',str(out/'bag'),'/scan','/odom','/tf','/tf_static','/clock','/gazebo/model_states'],'bag')
    with (out/'route.log').open('w') as log:
        route=subprocess.run([str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M3/M3-2/scripts/drive_route.py'),'--out',str(out),'--timeout',str(a.timeout)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=a.timeout+30)
    if route.returncode: raise RuntimeError('Survey route failed; raw data retained')
    print('SURVEY_FINISHED; qualifying actual graph and occupancy map',out,flush=True)
    import rclpy
    from rclpy.node import Node
    from slam_toolbox.srv import SerializePoseGraph
    rclpy.init(); node=Node('mapping_qualification'); client=node.create_client(SerializePoseGraph,'/slam_toolbox/serialize_map')
    try:
        if not client.wait_for_service(timeout_sec=20): raise RuntimeError('Pose graph serialization service missing')
        deadline=time.monotonic()+2
        while time.monotonic()<deadline: rclpy.spin_once(node,timeout_sec=.1)
        request=SerializePoseGraph.Request(); request.filename=str(out/'serialized_map')
        future=client.call_async(request); rclpy.spin_until_future_complete(node,future,timeout_sec=30)
        if not future.done() or future.result().result!=0: raise RuntimeError('Actual SLAM graph serialization failed')
        (out/'serialize_result.txt').write_text(str(future.result()))
    finally: node.destroy_node(); rclpy.shutdown()
    with (out/'save_map.log').open('w') as log:
        subprocess.run(['ros2','run','nav2_map_server','map_saver_cli','-f',str(out/'map'),'--ros-args','-p','use_sim_time:=true','-p','save_map_timeout:=15.0'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=45)
    with (out/'graph_analysis.txt').open('w') as log:
        subprocess.run([str(tool/'inspect_posegraph'),str(out/'serialized_map.posegraph')],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=30)
    graph=json.loads(next(line.split('POSEGRAPH_JSON ',1)[1] for line in (out/'graph_analysis.txt').read_text().splitlines() if 'POSEGRAPH_JSON ' in line))
    (out/'graph_analysis.json').write_text(json.dumps(graph,indent=2))
    with (out/'quality.log').open('w') as log:
        subprocess.run([str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M3/M3-2/scripts/eval_map.py'),'--map',str(out/'map.yaml'),'--out',str(out/'quality')],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=45)
    quality=json.loads((out/'quality/quality.json').read_text()); reasons=[]
    if quality['wall_points']<100: reasons.append('too_few_wall_observations')
    if quality['wall_max_deviation_m']>.10: reasons.append('wall_deviation_over_two_cells')
    if quality['loop_wall_double_clusters']>0: reasons.append('separated_wall_ghost_clusters')
    if not .90<=quality['gate_measured_free_width_m']<=1.05: reasons.append('gate_width_outside_expected_grid_band')
    historic=[e for e in graph['nonlocal_edges_id_gap_gt20'] if e['scan_time_gap_s']>30]
    if not historic: reasons.append('no_historic_nonlocal_graph_constraint')
    qualification=dict(status='PASS' if not reasons else 'FAIL',failures=reasons,quality=quality,
                       graph=dict(vertices=graph['vertices'],edges=graph['edges'],historic_constraints=len(historic)),
                       map_sha256=hashlib.sha256((out/'map.pgm').read_bytes()).hexdigest(),promoted=False)
    if reasons: raise RuntimeError('Map qualification failed: '+str(reasons))
    if a.promote:
        maps=ROOT/'M3/M3-2/maps'; maps.mkdir(exist_ok=True)
        shutil.copy2(out/'map.pgm',maps/'map.pgm'); shutil.copy2(out/'map.yaml',maps/'map.yaml')
        qualification['promoted']=True
        (maps/'map_manifest.json').write_text(json.dumps(dict(source_trial=str(out.relative_to(ROOT)),**qualification),indent=2))
    print('MAPPING_QUALIFICATION_PASS '+json.dumps(qualification),flush=True)
finally:
    for process in reversed(processes):
        if process.poll() is None: os.killpg(process.pid,signal.SIGINT)
    for process in reversed(processes):
        try: process.wait(timeout=12)
        except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL); process.wait()
    for stream in streams: stream.close()
    settings.update(finished=time.time(),qualification=qualification)
    (out/'settings.json').write_text(json.dumps(settings,indent=2))
    print('MAPPING_TRIAL',out,flush=True)
