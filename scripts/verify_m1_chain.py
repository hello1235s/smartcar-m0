import json
import os
import signal
import subprocess
import time
from pathlib import Path

os.environ['ROS_DOMAIN_ID'] = '61'
import rclpy
from rclpy.node import Node
from rcl_interfaces.srv import SetParameters, GetParameters
from rcl_interfaces.msg import Parameter, ParameterValue, ParameterType
from sensor_interfaces.msg import SensorData
from sensor_interfaces.srv import TriggerAlarm
from std_msgs.msg import Float32

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence' / 'M1-chain' / time.strftime('%Y%m%d_%H%M%S')
OUT.mkdir(parents=True, exist_ok=True)
processes, streams = [], []


def spawn(name, command):
    stream = (OUT / (name + '.log')).open('w')
    streams.append(stream)
    process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    processes.append(process)
    return process


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def spin(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        rclpy.spin_once(observer, timeout_sec=0.05)


def call(kind, service, request):
    client = observer.create_client(kind, service)
    assert client.wait_for_service(timeout_sec=5), service
    future = client.call_async(request)
    rclpy.spin_until_future_complete(observer, future, timeout_sec=5)
    assert future.done() and future.result() is not None, service
    response = future.result()
    observer.destroy_client(client)
    return response


def set_double(node, key, value):
    request = SetParameters.Request(parameters=[Parameter(name=key, value=ParameterValue(type=ParameterType.PARAMETER_DOUBLE, double_value=value))])
    return call(SetParameters, node + '/set_parameters', request).results[0]


rclpy.init()
observer = Node('contract_observer')
samples, processed = [], []
sub_a = observer.create_subscription(SensorData, '/sensor_data', lambda msg: samples.append((time.monotonic(), msg.status)), 20)
sub_b = observer.create_subscription(Float32, '/processed_distance', lambda msg: processed.append((time.monotonic(), msg.data)), 20)
report = {}
try:
    a = spawn('sensor', ['ros2', 'run', 'smartcar_training', 'node_a_sensor'])
    b = spawn('filter', ['ros2', 'run', 'smartcar_training', 'node_b_filter'])
    c = spawn('alarm', ['ros2', 'run', 'smartcar_training', 'node_c_alarm', '--ros-args', '-p', 'alarm_threshold:=2.0'])
    spin(3)
    assert set_double('/node_b_filter', 'alpha', 0.9).successful
    assert not set_double('/node_b_filter', 'alpha', 1.2).successful
    answer = call(TriggerAlarm, '/trigger_alarm', TriggerAlarm.Request(distance=0.1))
    assert answer.success
    spin(2)
    sampling_deadline = time.monotonic() + 8
    while (len(samples) < 35 or len(processed) < 30 or not any(status for _, status in samples)) and time.monotonic() < sampling_deadline:
        spin(0.25)
    assert len(samples) >= 35 and len(processed) >= 30, (len(samples), len(processed))
    report['sensor_hz'] = (len(samples)-1)/(samples[-1][0]-samples[0][0])
    report['processed_hz'] = (len(processed)-1)/(processed[-1][0]-processed[0][0])
    assert 8 < report['sensor_hz'] < 12 and 8 < report['processed_hz'] < 12, report
    report['invalid_status_samples'] = sum(status != 0 for _, status in samples)
    assert report['invalid_status_samples'] > 0
    assert 'float32 distance' == subprocess.check_output(['ros2', 'interface', 'show', 'sensor_interfaces/msg/SensorData'], text=True).splitlines()[0]
    stop(b)
    spin(2.5)
    for stream in streams:
        stream.flush()
    assert '[WARN] 报警服务超时' in (OUT/'alarm.log').read_text(), 'Missing service timeout after killing filter/server'
    report['timeout_after_server_killed'] = True
    for process in [a, c]:
        stop(process)
    spawn('robot1', ['ros2', 'launch', 'smartcar_training', 'bringup.launch.py', 'namespace:=robot1'])
    spawn('robot2', ['ros2', 'launch', 'smartcar_training', 'bringup.launch.py', 'namespace:=robot2', 'params_file:='+str(ROOT/'M1/M1-2/params_robot2.yaml')])
    spin(6)
    names = sorted(namespace.rstrip('/')+'/'+name for name, namespace in observer.get_node_names_and_namespaces() if namespace in ('/robot1', '/robot2'))
    expected = sorted('/'+ns+'/'+name for ns in ['robot1', 'robot2'] for name in ['node_a_sensor', 'node_b_filter', 'node_c_alarm'])
    assert names == expected, names
    report['namespaced_nodes'] = names
    report['thresholds'] = {}
    for namespace, expected_threshold in [('robot1', 0.3), ('robot2', 0.5)]:
        response = call(GetParameters, '/'+namespace+'/node_c_alarm/get_parameters', GetParameters.Request(names=['alarm_threshold']))
        assert response.values[0].double_value == expected_threshold
        report['thresholds'][namespace] = response.values[0].double_value
    result = subprocess.run(['ros2','launch','smartcar_training','bringup.launch.py','params_file:=/nope.yaml'], capture_output=True, text=True, timeout=12)
    (OUT/'missing_yaml.log').write_text(result.stdout+result.stderr)
    assert 'does not exist: /nope.yaml' in result.stdout+result.stderr and 'Traceback' not in result.stdout+result.stderr
    report['missing_yaml_human_error'] = True
    report['result'] = 'PASS'
finally:
    for process in processes:
        stop(process)
    for stream in streams:
        stream.close()
    observer.destroy_node()
    rclpy.shutdown()
    (OUT/'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False, indent=2))
(OUT.parent/'latest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
