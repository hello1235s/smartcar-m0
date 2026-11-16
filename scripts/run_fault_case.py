import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
ROOT=Path(__file__).resolve().parents[1]; os.environ['ROS_DOMAIN_ID']='68'
def api(action,**args):
    req=urllib.request.Request('http://127.0.0.1:8081/api/command',data=json.dumps(dict(action=action,**args)).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=25) as f: return json.load(f)
def state():
    with urllib.request.urlopen('http://127.0.0.1:8081/api/state') as f: return json.load(f)
rclpy.init(); node=Node('controlled_fault_experiment'); mode=node.create_publisher(String,'/simulator/mode',10)
api('NEW_RUN'); api('CLEAR_ESTOP'); api('LOAD_MODEL',path=str(ROOT/'M6/M6-1/models/best_fp32.onnx')); api('SET_PARAMS',values=dict(confidence=.25,perception_hz=10.,nav_speed=.4,scene='training_mock'))
run=Path(state()['run']); api('START'); time.sleep(3.5); mode.publish(String(data='camera_off')); time.sleep(2.5)
snapshot=state(); assert snapshot['referee']['state']=='PAUSED',snapshot['referee']
mode.publish(String(data='normal')); api('RESUME'); deadline=time.monotonic()+25
while not (run/'task_report.json').exists() and time.monotonic()<deadline: time.sleep(.2)
assert (run/'task_report.json').exists(); report=json.loads((run/'task_report.json').read_text()); assert report['degraded'] and report['result']=='SUCCESS'
api('STOP'); api('SEAL_RUN'); subprocess.run([str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M5/M5-4/quick_review.py'),str(run)],check=True)
(ROOT/'M5/experiments/fault_case.json').write_text(json.dumps(dict(run=str(run),paused_on_real_ROS_fault=True,report=report),indent=2)); print('CONTROLLED_FAULT_CASE_PASS',run)
node.destroy_node(); rclpy.try_shutdown()
