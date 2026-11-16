"""Reprocess recorded real Gazebo scans/odom/TF; serialize the actual SLAM graph."""
import os
from pathlib import Path
import signal
import subprocess
import time
import rclpy
from rclpy.node import Node
from slam_toolbox.srv import SerializePoseGraph
ROOT=Path(__file__).resolve().parents[1]; out=ROOT/'M3/M3-2/results'/('replay_'+time.strftime('%Y%m%d_%H%M%S')); out.mkdir(parents=True)
env=dict(os.environ,ROS_DOMAIN_ID='150'); os.environ['ROS_DOMAIN_ID']='150'
log=(out/'slam_debug.log').open('w'); baglog=(out/'bag_replay.log').open('w')
process=subprocess.Popen(['ros2','run','slam_toolbox','async_slam_toolbox_node','--ros-args','--params-file',str(ROOT/'M3/M3-2/config/slam_params.yaml'),'-p','debug_logging:=true','--log-level','slam_toolbox:=debug'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
rclpy.init(); node=Node('slam_graph_evidence'); client=node.create_client(SerializePoseGraph,'/slam_toolbox/serialize_map')
try:
    if not client.wait_for_service(timeout_sec=20): raise RuntimeError('SLAM serializer not available')
    playback=subprocess.run(['ros2','bag','play',str(ROOT/'M3/M3-2/results/20261116_212209/bag')],env=env,stdout=baglog,stderr=subprocess.STDOUT,timeout=240)
    assert playback.returncode==0
    # Remaining graph work and publication use wall time; simulation is deliberately frozen after playback.
    deadline=time.monotonic()+4
    while time.monotonic()<deadline: rclpy.spin_once(node,timeout_sec=.1)
    request=SerializePoseGraph.Request(); request.filename=str(out/'serialized_map')
    future=client.call_async(request); rclpy.spin_until_future_complete(node,future,timeout_sec=30)
    assert future.done(); (out/'serialize_result.txt').write_text(str(future.result()))
    saved=subprocess.run(['ros2','run','nav2_map_server','map_saver_cli','-f',str(out/'map_replay'),'--ros-args','-p','save_map_timeout:=15.0'],env=env,capture_output=True,text=True,timeout=40)
    (out/'map_saver.log').write_text(saved.stdout+saved.stderr); print('SLAM_GRAPH_SAVED',out,flush=True)
finally:
    if process.poll() is None: os.killpg(process.pid,signal.SIGINT)
    try: process.wait(timeout=8)
    except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL); process.wait()
    log.close(); baglog.close(); node.destroy_node(); rclpy.try_shutdown()
