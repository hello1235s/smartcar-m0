"""Load the unchanged PGM through native map_server and display it in actual RViz."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'M3/common'))
from experiment_lock import acquire
from process_cleanup import terminate_owned_tree
from navigation_transport import configure
original_libraries=os.environ.get('LD_LIBRARY_PATH','').split(':')
configure(ROOT)
# dlopen's startup search path is fixed before Python modifies os.environ.
if str(ROOT/'vendor/m3-dds/opt/ros/humble/lib') not in original_libraries:
    os.execv(sys.executable,[sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]])
lock=acquire()
p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=90);p.add_argument('--domain',type=int,default=181);a=p.parse_args()
os.environ['ROS_DOMAIN_ID']=str(a.domain)
out=ROOT/'M3/M3-2/results'/(time.strftime('%Y%m%d_%H%M%S')+'_native_rviz_map');out.mkdir(parents=True)
mapfile=ROOT/'M3/M3-2/maps/map.yaml';image=ROOT/'M3/M3-2/maps/map.pgm'
before={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [mapfile,image]}
processes=[];logs=[];record=dict(status='running',map_hashes=before,domain=a.domain)
def start(command,name,env=None):
    log=(out/(name+'.log')).open('w');logs.append(log)
    process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);processes.append(process);return process
try:
    server=start(['ros2','run','nav2_map_server','map_server','--ros-args','-r','__node:=guide_map_server',
                  '-p','yaml_filename:='+str(mapfile),'-p','use_sim_time:=false'],'map_server')
    for transition in ['configure','activate']:
        with (out/(transition+'.log')).open('w') as log:
            subprocess.run(['ros2','lifecycle','set','/guide_map_server',transition],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=40)
    import rclpy
    from rclpy.node import Node
    from nav_msgs.srv import GetMap
    rclpy.init();node=Node('native_map_display_observer');client=node.create_client(GetMap,'/guide_map_server/map')
    assert client.wait_for_service(timeout_sec=10)
    future=client.call_async(GetMap.Request());rclpy.spin_until_future_complete(node,future,timeout_sec=10)
    assert future.done() and future.result();message=future.result().map
    import numpy as np
    values=np.asarray(message.data)
    counts=dict(occupied=int(np.count_nonzero(values==100)),free=int(np.count_nonzero(values==0)),unknown=int(np.count_nonzero(values==-1)))
    assert counts==dict(occupied=1600,free=24784,unknown=12820),counts
    record.update(native_getmap_counts=counts,width=message.info.width,height=message.info.height)
    node.destroy_node();rclpy.shutdown()
    rviz=start(['ros2','run','smartcar_nav_checks','rviz_showcase','--config',str(ROOT/'M3/M3-3/config/exam_navigation.rviz'),
                '--out',str(out),'--ros-args','-p','use_sim_time:=false'],'rviz',dict(os.environ,LIBGL_ALWAYS_SOFTWARE='1'))
    record['rviz_rendering']='Mesa software rendering for RViz only; simulation/control environment unchanged'
    time.sleep(12)
    render=out/'native_rviz_render.png'
    import cv2
    pixels=cv2.imread(str(render))
    assert pixels is not None and float(pixels.std())>5,'RViz internal framebuffer is missing or blank'
    record['native_rviz_capture']=json.loads((out/'native_rviz_render.json').read_text())
    record['capture_method']='RViz internal render window, not an XWayland screen readback'
    deadline=time.monotonic()+max(0,a.seconds-12)
    while time.monotonic()<deadline:
        if rviz.poll() is not None or server.poll() is not None:raise RuntimeError('Map/RViz closed during display')
        time.sleep(.2)
    assert before=={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [mapfile,image]}
    record['status']='PASS'
except BaseException as error:
    record.update(status='FAIL',error=str(error));raise
finally:
    for process in reversed(processes):terminate_owned_tree(process)
    for log in logs:log.close()
    (out/'verification.json').write_text(json.dumps(record,indent=2));print('NATIVE_RVIZ_MAP',out,json.dumps(record),flush=True)
