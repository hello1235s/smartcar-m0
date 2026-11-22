import json
import math
from pathlib import Path

import cv2
import numpy as np
import yaml
import rclpy
import message_filters
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.time import Time
from rclpy.clock import Clock, ClockType
from sensor_msgs.msg import LaserScan, Image, CameraInfo
from geometry_msgs.msg import TransformStamped
from tf2_ros import Buffer, TransformListener, StaticTransformBroadcaster, TransformException
from cv_bridge import CvBridge


def quaternion(rpy):
    r, p, y = (v / 2 for v in rpy)
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return (sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy)


def matrix(q):
    x, y, z, w = q.x, q.y, q.z, q.w
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


class Projection(Node):
    def __init__(self):
        super().__init__('laser_camera_projection')
        for key, value in [('extrinsics_file', 'extrinsics.yaml'), ('output_dir', '.'), ('max_images', 3), ('slop', 0.05)]:
            self.declare_parameter(key, value)
        with open(self.get_parameter('extrinsics_file').value, encoding='utf-8') as source:
            self.calibration = yaml.safe_load(source)
        self.intrinsics = self.calibration['camera_intrinsics']
        self.directory = Path(self.get_parameter('output_dir').value)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.bridge = CvBridge()
        self.count = 0
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.static = StaticTransformBroadcaster(self)
        transforms = []
        for parent, child, xyz, rpy in [('map', 'odom', [0, 0, 0], [0, 0, 0]), ('odom', 'base_link', [0, 0, 0], [0, 0, 0])]:
            transforms.append(self.transform(parent, child, xyz, rpy))
        for child in ['laser_link', 'camera_link']:
            item = self.calibration[child]
            transforms.append(self.transform(item['parent'], child, item['xyz'], item.get('rpy', [0, 0, 0])))
        self.static.sendTransform(transforms)
        self.transforms = transforms
        self.create_timer(1.0, lambda: self.static.sendTransform(self.transforms), clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.publisher = self.create_publisher(Image, '/projection/debug_image', 5)
        self.info = self.create_subscription(CameraInfo, '/camera/camera_info', self.check_intrinsics, 10)
        self.scan = message_filters.Subscriber(self, LaserScan, '/scan')
        self.image = message_filters.Subscriber(self, Image, '/camera/image_raw')
        self.sync = message_filters.ApproximateTimeSynchronizer([self.scan, self.image], 100, self.get_parameter('slop').value)
        self.sync.registerCallback(self.project)
        self.clock_log = (self.directory / 'clock_observations.jsonl').open('a', encoding='utf-8')
        self.add_on_set_parameters_callback(self.parameter_change)

    def parameter_change(self, parameters):
        from rcl_interfaces.msg import SetParametersResult
        for item in parameters:
            if item.name == 'use_sim_time':
                self.get_logger().info('CLOCK_MODE_CHANGE use_sim_time=%s' % item.value)
        return SetParametersResult(successful=True)

    def check_intrinsics(self, message):
        k = self.intrinsics
        if not np.allclose([message.k[0], message.k[4], message.k[2], message.k[5]], [k['fx'], k['fy'], k['cx'], k['cy']]):
            self.get_logger().warning('CameraInfo differs from extrinsics YAML; YAML remains the calibration source', throttle_duration_sec=5)

    def transform(self, parent, child, xyz, rpy):
        value = TransformStamped()
        value.header.stamp = self.get_clock().now().to_msg()
        value.header.frame_id, value.child_frame_id = parent, child
        value.transform.translation.x, value.transform.translation.y, value.transform.translation.z = map(float, xyz)
        q = quaternion(rpy)
        value.transform.rotation.x, value.transform.rotation.y, value.transform.rotation.z, value.transform.rotation.w = q
        return value

    def project(self, scan, message):
        try:
            transform = self.buffer.lookup_transform('camera_link', scan.header.frame_id, Time.from_msg(scan.header.stamp), timeout=Duration(seconds=0.02))
        except TransformException as error:
            self.get_logger().warning(str(error), throttle_duration_sec=2)
            return
        ranges = np.asarray(scan.ranges)
        angles = scan.angle_min + np.arange(len(ranges)) * scan.angle_increment
        valid = np.isfinite(ranges) & (ranges >= scan.range_min) & (ranges <= scan.range_max)
        points = np.column_stack((ranges[valid] * np.cos(angles[valid]), ranges[valid] * np.sin(angles[valid]), np.zeros(np.count_nonzero(valid))))
        t = transform.transform.translation
        points = points @ matrix(transform.transform.rotation).T + np.array([t.x, t.y, t.z])
        forward = points[:, 0] > 1e-5
        points, distances = points[forward], ranges[valid][forward]
        k = self.intrinsics
        u = np.rint(k['fx'] * (-points[:, 1]) / points[:, 0] + k['cx']).astype(int)
        v = np.rint(k['fy'] * (-points[:, 2]) / points[:, 0] + k['cy']).astype(int)
        image = self.bridge.imgmsg_to_cv2(message, desired_encoding='rgb8').copy()
        colored = 0
        point_records = []
        beam_indices = np.flatnonzero(valid)[forward]
        for x, y, distance, beam, camera_point in zip(u, v, distances, beam_indices, points):
            if 0 <= x < message.width and 0 <= y < message.height:
                weight = float(np.clip((distance - scan.range_min) / (scan.range_max - scan.range_min), 0, 1))
                cv2.circle(image, (int(x), int(y)), 3, (int(255*(1-weight)), 0, int(255*weight)), -1)
                colored += 1
                point_records.append(dict(beam_index=int(beam), distance_m=float(distance),
                                          pixel=[int(x), int(y)], camera_body_xyz_m=camera_point.tolist()))
        output = self.bridge.cv2_to_imgmsg(image, encoding='rgb8')
        output.header = message.header
        self.publisher.publish(output)
        self.count += 1
        if self.count <= self.get_parameter('max_images').value:
            cv2.imwrite(str(self.directory / ('projection_%03d.png' % self.count)), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            correspondence = dict(image='projection_%03d.png' % self.count,
                                  scan_stamp_ns=Time.from_msg(scan.header.stamp).nanoseconds,
                                  image_stamp_ns=Time.from_msg(message.header.stamp).nanoseconds,
                                  source_frame=scan.header.frame_id, target_frame='camera_link',
                                  points=point_records)
            (self.directory / ('projection_%03d.points.json' % self.count)).write_text(
                json.dumps(correspondence, indent=2), encoding='utf-8')
        self.clock_log.write(json.dumps({'pair': self.count, 'scan_s': Time.from_msg(scan.header.stamp).nanoseconds / 1e9,
                                         'image_s': Time.from_msg(message.header.stamp).nanoseconds / 1e9,
                                         'node_s': self.get_clock().now().nanoseconds / 1e9,
                                         'use_sim_time': self.get_parameter('use_sim_time').value, 'visible_points': colored,
                                         'median_projected_v': float(np.median(v[(u >= 0) & (u < message.width) & (v >= 0) & (v < message.height)])) if colored else None}) + '\n')
        self.clock_log.flush()


def main():
    rclpy.init()
    node = Projection()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.clock_log.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
