"""Measure actual ROS outputs for baseline, each one-sided change, and full optimization."""
import argparse
import json
import os
import signal
import re
import subprocess
import time
from pathlib import Path

os.environ['ROS_DOMAIN_ID'] = '62'
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=24)
    parser.add_argument('--variants', default='baseline,publisher_only,processor_only,optimized')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    out = root / 'results' / time.strftime('%Y%m%d_%H%M%S')
    out.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    rows = []
    for label, camera, processor in [('baseline', 'baseline/camera_pub.py', 'baseline/image_proc.py'),
                                      ('publisher_only', 'camera_pub.py', 'baseline/image_proc.py'),
                                      ('processor_only', 'baseline/camera_pub.py', 'image_proc.py'),
                                      ('optimized', 'camera_pub.py', 'image_proc.py')]:
        if label not in args.variants.split(','):
            continue
        handles = [(out/(label+'_'+name+'.log')).open('w') for name in ['camera', 'processor']]
        processes = [subprocess.Popen(['/usr/bin/python3', str(root/path)], stdout=handle, stderr=subprocess.STDOUT, start_new_session=True) for path, handle in zip([camera, processor], handles)]
        node = Node('performance_observer')
        output_times, control_times, delays, source_stamps = [], [], [], []
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)

        def receive(message):
            now = time.monotonic()
            if now < warm:
                return
            output_times.append(now)
            stamp = message.header.stamp.sec + message.header.stamp.nanosec / 1e9
            delays.append((time.time()-stamp)*1000)
            source_stamps.append(stamp)
            assert message.encoding == 'mono8' and message.width == 640 and message.height == 480

        node.create_subscription(Image, '/perception/result', receive, qos)
        node.create_subscription(Twist, '/control/cmd', lambda msg: control_times.append(time.monotonic()) if time.monotonic() >= warm else None, 10)
        warm = time.monotonic()+5
        deadline = warm+args.seconds
        try:
            while time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=0.05)
        finally:
            for process in processes:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGINT)
                    try:
                        process.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
            for handle in handles:
                handle.close()
            node.destroy_node()
        rate = lambda times: (len(times)-1)/(times[-1]-times[0]) if len(times) > 1 else 0
        row = {'variant': label, 'measurement_s': args.seconds, 'output_hz': rate(output_times), 'control_hz': rate(control_times), 'p50_ms': float(np.percentile(delays, 50)) if delays else None, 'p95_ms': float(np.percentile(delays, 95)) if delays else None, 'output_count': len(output_times), 'output_stamps_unique': len(set(source_stamps)) == len(source_stamps)}
        matches = re.findall(r'(?:平均\s+([0-9.]+)\s+Hz|frames,\s+([0-9.]+)\s+Hz)', (out/(label+'_camera.log')).read_text())
        row['input_hz_self_reported'] = float(next(value for value in matches[-1] if value)) if matches else None
        rows.append(row)
        (out/'measurements.json').write_text(json.dumps(rows, indent=2))
        print(json.dumps(row), flush=True)
        time.sleep(1)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
