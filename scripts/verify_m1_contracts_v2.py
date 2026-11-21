"""Black-box ROS acceptance: fields, exact filtering, invalid data and timeout."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
# This file is first executed from tmp; later the identical public entry is scripts/.
os.environ['ROS_DOMAIN_ID']='68'
sys.path.insert(0,str(ROOT/'M3/common'))
from process_cleanup import terminate_owned_tree
import rclpy
from rclpy.node import Node
from rcl_interfaces.srv import GetParameters,SetParameters
from rcl_interfaces.msg import Parameter,ParameterValue,ParameterType
from sensor_interfaces.msg import SensorData
from sensor_interfaces.srv import TriggerAlarm
from std_msgs.msg import Float32

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
processes=[];streams=[];record=dict(status='running',tests={})
rclpy.init();node=Node('m1_contract_observer_v2');ns='/contract_'+str(os.getpid())
def spin(seconds):
    until=time.monotonic()+seconds
    while time.monotonic()<until:rclpy.spin_once(node,timeout_sec=.02)
def wait(predicate,seconds=5):
    until=time.monotonic()+seconds
    while not predicate() and time.monotonic()<until:rclpy.spin_once(node,timeout_sec=.02)
    assert predicate(),'Timed out waiting for contract condition'
def start(name,executable):
    log=(out/(name+'.log')).open('w');streams.append(log)
    process=subprocess.Popen(['ros2','run','smartcar_training',executable,'--ros-args','-r','__ns:='+ns],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    processes.append(process);return process
def call(kind,path,request):
    client=node.create_client(kind,path)
    assert client.wait_for_service(timeout_sec=5),path
    began=time.monotonic();future=client.call_async(request)
    rclpy.spin_until_future_complete(node,future,timeout_sec=4)
    assert future.done() and future.result() is not None,path
    response=future.result();elapsed=time.monotonic()-began;node.destroy_client(client);return response,elapsed
def change(value):
    request=SetParameters.Request(parameters=[Parameter(name='alpha',value=ParameterValue(type=ParameterType.PARAMETER_DOUBLE,double_value=value))])
    return call(SetParameters,ns+'/node_b_filter/set_parameters',request)[0].results[0]
values=[];pub=node.create_publisher(SensorData,ns+'/sensor_data',10)
sub=node.create_subscription(Float32,ns+'/processed_distance',lambda m:values.append(m.data),10)
def publish(distance,status=0,unit='m',expect=None):
    count=len(values);message=SensorData(distance=float(distance),unit=unit,status=status)
    message.stamp=node.get_clock().now().to_msg();pub.publish(message)
    if expect is None:spin(.25);assert len(values)==count,('Invalid sample emitted output',values)
    else:
        wait(lambda:len(values)>count,2)
        assert len(values)==count+1 and abs(values[-1]-expect)<1e-6,(values[-1],expect)
try:
    actual=list(SensorData.get_fields_and_field_types().items())
    assert [name for name,_ in actual]==['distance','unit','stamp','status'],actual
    native=subprocess.check_output(['ros2','interface','show','sensor_interfaces/msg/SensorData'],cwd=ROOT,text=True)
    flat=[line.strip() for line in native.splitlines() if line and not line[0].isspace() and not line.startswith('#')]
    assert flat==['float32 distance','string unit','builtin_interfaces/Time stamp','uint8 status'],flat
    record['tests']['message_contract']=dict(fields=flat,pass_check=True)
    filtering=start('filter','node_b_filter')
    call(GetParameters,ns+'/node_b_filter/get_parameters',GetParameters.Request(names=['alpha']))
    wait(lambda:pub.get_subscription_count()>0)
    publish(1.,expect=1.)
    for status in [1,2]:publish(0.,status=status)
    publish(0.,unit='cm');publish(float('nan'))
    publish(0.,expect=.7)
    assert change(.9).successful
    assert not change(1.2).successful and not change(float('nan')).successful
    response,_=call(GetParameters,ns+'/node_b_filter/get_parameters',GetParameters.Request(names=['alpha']))
    assert response.values[0].double_value==.9
    publish(.5,expect=.52)
    reply,_=call(TriggerAlarm,ns+'/trigger_alarm',TriggerAlarm.Request(distance=.1));assert reply.success
    terminate_owned_tree(filtering);processes.remove(filtering)
    text=(out/'filter.log').read_text();assert 'invalid sensor sample ignored: status=1' in text and 'invalid sensor sample ignored: status=2' in text
    record['tests']['filter_values']=dict(actual=list(values),expected=[1.,.7,.52],invalid_samples_emit_nothing=True,dynamic_alpha_and_rejected_nan=True,alarm_service=True)
    alarm=start('alarm_without_server','node_c_alarm')
    response,_=call(GetParameters,ns+'/node_c_alarm/get_parameters',GetParameters.Request(names=['alarm_threshold','service_timeout']))
    assert [x.double_value for x in response.values]==[.3,1.]
    distance=node.create_publisher(Float32,ns+'/processed_distance',10);wait(lambda:distance.get_subscription_count()>=2)
    began_epoch=time.time();distance.publish(Float32(data=.1));spin(.2)
    response,elapsed=call(GetParameters,ns+'/node_c_alarm/get_parameters',GetParameters.Request(names=['alarm_threshold']))
    assert elapsed<.5,('Parameter service blocked during alarm timeout',elapsed)
    spin(1.5);terminate_owned_tree(alarm);processes.remove(alarm)
    log=(out/'alarm_without_server.log').read_text()
    line=next(line for line in log.splitlines() if '[WARN] 报警服务超时' in line)
    stamp=re.search(r'\[(\d{10}\.\d+)\]',line);assert stamp,line
    observed_delay=float(stamp[1])-began_epoch
    assert .95<=observed_delay<=1.5,observed_delay
    record['tests']['nonblocking_timeout']=dict(configured_timeout_s=1.,observed_warning_delay_s=observed_delay,parameter_roundtrip_while_waiting_s=elapsed,raw_warning=line)
    record['status']='PASS'
except BaseException as error:
    record.update(status='FAIL',error=str(error));raise
finally:
    for process in processes:terminate_owned_tree(process)
    for stream in streams:stream.close()
    node.destroy_node();rclpy.shutdown()
    (out/'results.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
print(json.dumps(record,ensure_ascii=False),flush=True)
