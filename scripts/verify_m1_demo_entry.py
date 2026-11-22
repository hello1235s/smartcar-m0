"""Check that the public shell entry exposes the exact root M1 interfaces."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'M3/common'))
from process_cleanup import terminate_owned_tree
os.environ['ROS_DOMAIN_ID']='71'
import rclpy
from rclpy.node import Node
from rcl_interfaces.srv import GetParameters
from sensor_interfaces.srv import TriggerAlarm
out=ROOT/'evidence/M1-demo-entry'/time.strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
log=(out/'chain.log').open('w');process=subprocess.Popen(['bash','scripts/run_m1_demo.sh','chain'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
rclpy.init();node=Node('root_demo_observer');record=dict(status='running')
try:
    parameters=node.create_client(GetParameters,'/node_b_filter/get_parameters');assert parameters.wait_for_service(timeout_sec=20)
    request=GetParameters.Request(names=['alpha']);future=parameters.call_async(request)
    rclpy.spin_until_future_complete(node,future,timeout_sec=5);assert future.done() and future.result().values[0].double_value==.3
    service=node.create_client(TriggerAlarm,'/trigger_alarm');assert service.wait_for_service(timeout_sec=5)
    future=service.call_async(TriggerAlarm.Request(distance=.1));rclpy.spin_until_future_complete(node,future,timeout_sec=5)
    assert future.done() and future.result().success
    deadline=time.monotonic()+5;expected={(name,'/') for name in ['node_a_sensor','node_b_filter','node_c_alarm']}
    while time.monotonic()<deadline and not expected.issubset(set(node.get_node_names_and_namespaces())):rclpy.spin_once(node,timeout_sec=.1)
    assert expected.issubset(set(node.get_node_names_and_namespaces()))
    names={name for name,_ in node.get_topic_names_and_types()};assert {'/sensor_data','/processed_distance'}.issubset(names)
    record.update(status='PASS',root_nodes=sorted(expected),root_topics=sorted(names),manual_alarm_reply=True)
finally:
    terminate_owned_tree(process);log.close();node.destroy_node();rclpy.shutdown()
    (out/'results.json').write_text(json.dumps(record,indent=2));print('ROOT_DEMO_ENTRY',out,json.dumps(record),flush=True)
