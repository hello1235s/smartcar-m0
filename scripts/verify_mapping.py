import os
import signal
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'M3/M3-2/results'/time.strftime('%Y%m%d_%H%M%S'); OUT.mkdir(parents=True)
env=dict(os.environ,ROS_DOMAIN_ID='65',GAZEBO_MASTER_URI='http://127.0.0.1:11376',GAZEBO_MODEL_DATABASE_URI='',DISPLAY=':0')
processes=[]; streams=[]
def start(args,name):
    stream=(OUT/(name+'.log')).open('w'); streams.append(stream)
    proc=subprocess.Popen(args,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    processes.append(proc); return proc
try:
    start(['ros2','launch','smart_car_description','sim.launch.py','world:='+str(ROOT/'M3/M3-2/worlds/scene.world'),'x:=1.0','y:=1.0'],'simulation')
    start(['ros2','run','slam_toolbox','async_slam_toolbox_node','--ros-args','--params-file',str(ROOT/'M3/M3-2/config/slam_params.yaml')],'slam')
    start(['ros2','bag','record','-o',str(OUT/'bag'),'/scan','/odom','/tf','/tf_static','/clock'],'bag')
    result=subprocess.run([str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M3/M3-2/scripts/drive_route.py'),'--out',str(OUT)],env=env,capture_output=True,text=True,timeout=650)
    (OUT/'route.log').write_text(result.stdout+result.stderr); print(result.stdout+result.stderr,flush=True)
    # Save even an incomplete actual map; qualification remains based on route completion.
    maps=ROOT/'M3/M3-2/maps'; maps.mkdir(exist_ok=True)
    saved=subprocess.run(['ros2','run','nav2_map_server','map_saver_cli','-f',str(maps/'map'),'--ros-args','-p','use_sim_time:=true','-p','save_map_timeout:=15.0'],env=env,capture_output=True,text=True,timeout=45)
    (OUT/'save_map.log').write_text(saved.stdout+saved.stderr)
    assert saved.returncode==0,saved.stderr
    assert result.returncode==0,'Survey route incomplete: see '+str(OUT/'route.log')
    print('MAPPING_PASS '+str(OUT),flush=True)
finally:
    for proc in reversed(processes):
        if proc.poll() is None: os.killpg(proc.pid,signal.SIGINT)
    for proc in reversed(processes):
        try: proc.wait(timeout=10)
        except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL); proc.wait()
    for stream in streams: stream.close()
