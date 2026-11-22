"""Verify the new single-command two-namespace launch through live ROS services."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'M3/common'))
from process_cleanup import terminate_owned_tree
os.environ['ROS_DOMAIN_ID']='72'
import rclpy
from rclpy.node import Node
from rcl_interfaces.srv import GetParameters,SetParameters
from rcl_interfaces.msg import Parameter,ParameterValue,ParameterType
out=ROOT/'evidence/M1-dual-launch'/time.strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
log=(out/'launch.log').open('w');process=subprocess.Popen(['ros2','launch','smartcar_training','dual_bringup.launch.py'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
rclpy.init();node=Node('dual_launch_observer');record=dict(status='running',command='ros2 launch smartcar_training dual_bringup.launch.py')
def call(kind,name,request):
    client=node.create_client(kind,name);assert client.wait_for_service(timeout_sec=20),name
    future=client.call_async(request);rclpy.spin_until_future_complete(node,future,timeout_sec=5)
    assert future.done() and future.result() is not None,name
    result=future.result();node.destroy_client(client);return result
def get(robot,name):
    request=GetParameters.Request(names=[name]);return call(GetParameters,'/'+robot+'/node_'+('b_filter' if name=='alpha' else 'c_alarm')+'/get_parameters',request).values[0].double_value
try:
    threshold1,threshold2=get('robot1','alarm_threshold'),get('robot2','alarm_threshold')
    assert abs(threshold1-.3)<1e-9 and abs(threshold2-.5)<1e-9
    change=SetParameters.Request(parameters=[Parameter(name='alpha',value=ParameterValue(type=ParameterType.PARAMETER_DOUBLE,double_value=.9))])
    assert call(SetParameters,'/robot1/node_b_filter/set_parameters',change).results[0].successful
    assert get('robot1','alpha')==.9 and get('robot2','alpha')==.7
    deadline=time.monotonic()+8;expected={(name,'/'+robot) for robot in ['robot1','robot2'] for name in ['node_a_sensor','node_b_filter','node_c_alarm']}
    while not expected.issubset(set(node.get_node_names_and_namespaces())) and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.1)
    assert expected.issubset(set(node.get_node_names_and_namespaces()))
    endpoints={}
    for robot in ['robot1','robot2']:
        path='/'+robot+'/sensor_data';values=node.get_publishers_info_by_topic(path)+node.get_subscriptions_info_by_topic(path)
        assert len(values)>=2 and all(v.node_namespace=='/'+robot for v in values)
        endpoints[path]=[dict(name=v.node_name,namespace=v.node_namespace) for v in values]
    record.update(status='PASS',nodes=sorted(expected),thresholds=[threshold1,threshold2],alpha_after_change=[get('robot1','alpha'),get('robot2','alpha')],endpoints=endpoints)
finally:
    terminate_owned_tree(process);log.close();node.destroy_node();rclpy.shutdown()
    (out/'results.json').write_text(json.dumps(record,indent=2));print('DUAL_LAUNCH',out,json.dumps(record),flush=True)
