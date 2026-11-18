import argparse
import csv
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import message_filters
import rosbag2_py
import rclpy
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Image, LaserScan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bag')
    parser.add_argument('--out', default='sync_sweep.csv')
    args = parser.parse_args()
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=args.bag, storage_id='sqlite3'), rosbag2_py.ConverterOptions('', ''))
    events = []
    scans = 0
    while reader.has_next():
        topic, payload, _ = reader.read_next()
        if topic in ('/scan', '/camera/image_raw'):
            message = deserialize_message(payload, LaserScan if topic == '/scan' else Image)
            events.append((0 if topic == '/scan' else 1, SimpleNamespace(header=message.header)))
            scans += topic == '/scan'
    rclpy.init()
    rows = []
    for milliseconds in [20, 40, 50, 60, 100, 150]:
        sources = [message_filters.SimpleFilter(), message_filters.SimpleFilter()]
        synchronizer = message_filters.ApproximateTimeSynchronizer(sources, 100, milliseconds / 1000)
        differences = []
        synchronizer.registerCallback(lambda a, b: differences.append(abs((a.header.stamp.sec-b.header.stamp.sec)*1000 + (a.header.stamp.nanosec-b.header.stamp.nanosec)/1e6)))
        for index, message in events:
            sources[index].signalMessage(message)
        rows.append({'slop_ms': milliseconds, 'paired': len(differences), 'scan_frames': scans, 'median_dt_ms': float(np.median(differences)) if differences else None, 'p95_dt_ms': float(np.percentile(differences, 95)) if differences else None})
    rclpy.shutdown()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, 'w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(rows)


if __name__ == '__main__':
    main()
