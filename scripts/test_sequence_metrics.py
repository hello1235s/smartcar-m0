import json
import os
from pathlib import Path
import signal
import subprocess
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
ROOT=Path(__file__).resolve().parents[1]; os.environ['ROS_DOMAIN_ID']='151'
p=subprocess.Popen([str(ROOT/'install_ros/dashboard_tools/lib/dashboard_tools/dashboard_aggregator'),'--ros-args','-p','topic_patterns:=["/test/*"]'],env=os.environ,start_new_session=True,stdout=subprocess.DEVNULL)
rclpy.init(); n=Node('sequence_verifier'); latest={}
def on(m): latest.update(json.loads(m.data).get('topics',{}))
n.create_subscription(String,'/dashboard/metrics',on,10); a=n.create_publisher(String,'/test/known_loss',10); b=n.create_publisher(String,'/test/invalid_seq',10)
def spin(s):
    end=time.monotonic()+s
    while time.monotonic()<end: rclpy.spin_once(n,timeout_sec=.02)
try:
    spin(2)
    for x,y in [(1,1),(2,2),(5,2)]: a.publish(String(data=json.dumps(dict(seq=x)))); b.publish(String(data=json.dumps(dict(seq=y)))); spin(.2)
    spin(.4); assert abs(latest['/test/known_loss']['loss_rate']-.4)<1e-6; assert latest['/test/invalid_seq']['loss_rate'] is None
    out=ROOT/'evidence/M5-hot-switch/sequence_metrics.json'; out.write_text(json.dumps(latest,indent=2)); print('SEQUENCE_METRICS_PASS')
finally:
    n.destroy_node(); rclpy.try_shutdown(); os.killpg(p.pid,signal.SIGINT); p.wait(timeout=5)
