import json
import os
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ['ROS_DOMAIN_ID'] = '64'
import rclpy
from rclpy.node import Node
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter, ParameterValue, ParameterType
TASK = ROOT/'M1/M1-3'
OUT = TASK/'results'/time.strftime('%Y%m%d_%H%M%S')
OUT.mkdir(parents=True)
env = dict(os.environ, ROS_DOMAIN_ID='64', DISPLAY=':0', XDG_RUNTIME_DIR='/run/user/'+str(os.getuid()), QT_QPA_PLATFORM='xcb')
python = str(ROOT/'.venv-ros/bin/python')
processes, streams = [], []
rclpy.init()
control = Node('projection_contract_controller')


def command(name, args, timeout=60):
    result = subprocess.run(args, env=env, cwd=OUT, capture_output=True, text=True, timeout=timeout)
    (OUT/(name+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode:
        raise RuntimeError(name+' failed: '+(result.stdout+result.stderr)[-1600:])
    return result


def start(name, args):
    stream = (OUT/(name+'.log')).open('w')
    streams.append(stream)
    process = subprocess.Popen(args, env=env, cwd=OUT, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    processes.append(process)
    return process


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def set_clock(name, value):
    client = control.create_client(SetParameters, '/'+name+'/set_parameters')
    assert client.wait_for_service(timeout_sec=10), 'Missing parameter service: '+name
    request = SetParameters.Request(parameters=[Parameter(name='use_sim_time', value=ParameterValue(type=ParameterType.PARAMETER_BOOL, bool_value=value))])
    future = client.call_async(request)
    rclpy.spin_until_future_complete(control, future, timeout_sec=5)
    assert future.done() and future.result().results[0].successful
    (OUT/('clock_'+str(value)+'_'+name+'.log')).write_text('SetParameters successful: use_sim_time='+str(value))
    control.destroy_client(client)


report = {}
try:
    for variant, frames, extra in [('default', 40, []), ('nondefault', 80, ['--laser-z','0.45','--camera-z','0.75','--fx','420','--fy','440'])]:
        directory = OUT/variant
        directory.mkdir()
        bag, extrinsics = directory/'bag', directory/'extrinsics.yaml'
        command('generate_'+variant, [python, str(TASK/'make_bag.py'), '--frames', str(frames), '--seed', '7', '--out', str(bag), '--extrinsics', str(extrinsics), *extra])
        if variant == 'nondefault':
            command('sweep', [python, str(TASK/'sweep_sync.py'), str(bag), '--out', str(directory/'sync_sweep.csv')])
        project = start('projection_'+variant, [python, str(TASK/'projection_node.py'), '--ros-args', '-p', 'use_sim_time:=true', '-p', 'extrinsics_file:='+str(extrinsics), '-p', 'output_dir:='+str(directory)])
        viewer = start('viewer_'+variant, ['/usr/bin/python3', str(TASK/'clock_viewer.py'), '--seconds', '23', '--out', str(directory/'clock_switch_demo.avi'), '--ros-args', '-p', 'use_sim_time:=true'])
        time.sleep(3)
        play = start('play_'+variant, ['ros2', 'bag', 'play', str(bag), '--clock', '--rate', '0.5' if viewer else '1.0'])
        if variant == 'nondefault':
            time.sleep(4)
            for name in ['laser_camera_projection', 'projection_clock_viewer']:
                set_clock(name, False)
            time.sleep(4)
            for name in ['laser_camera_projection', 'projection_clock_viewer']:
                set_clock(name, True)
        play.wait(timeout=40)
        if viewer:
            viewer.wait(timeout=15)
            assert viewer.returncode == 0, (OUT/('viewer_'+variant+'.log')).read_text()[-1500:]
            command('tf_tree', ['ros2', 'run', 'tf2_tools', 'view_frames'], timeout=20)
        stop(project)
        images = list(directory.glob('projection_*.png'))
        records = [json.loads(line) for line in (directory/'clock_observations.jsonl').read_text().splitlines()]
        assert len(images) == 3 and records and min(row['visible_points'] for row in records) > 0
        report[variant] = {'paired_frames': len(records), 'images': [p.name for p in images], 'clock_modes': sorted(set(row['use_sim_time'] for row in records)), 'median_v_first': records[0]['median_projected_v']}
        if variant == 'nondefault':
            assert report[variant]['clock_modes'] == [False, True], report
            assert (directory/'clock_switch_demo.avi').stat().st_size > 10000
    report['result'] = 'PASS'
finally:
    for process in processes:
        stop(process)
    for stream in streams:
        stream.close()
    control.destroy_node()
    rclpy.shutdown()
    (OUT/'results.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
