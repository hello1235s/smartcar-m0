"""Vectorized implementation of the supplied deterministic camera (640x480)."""
import time
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image

CAMERA_HZ = 32.0


class CameraSim(Node):
    def __init__(self):
        super().__init__('camera_sim')
        self.pub = self.create_publisher(Image, '/camera/image_raw', QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE))
        self.bridge = CvBridge()
        cv2.setNumThreads(1)
        self.pattern = (np.arange(480, dtype=np.uint16)[:, None] * 13 + np.arange(640, dtype=np.uint16)[None, :]) & 255
        self.frame = np.empty((480, 640, 3), dtype=np.uint8)
        self.frame[:, :, 2] = 60
        self.seq = self.count = 0
        self.started = time.monotonic()
        self.create_timer(1 / CAMERA_HZ, self.tick)
        self.create_timer(3.0, self.report)

    def tick(self):
        self.seq += 1
        plane = ((self.pattern + (self.seq & 255)) & 255).astype(np.uint8)
        self.frame[:, :, 0] = plane
        self.frame[:, :, 1] = plane
        # Processing needs grayscale only: retain the exact BGR->gray values
        # while sending one byte rather than three per pixel.
        gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        message = self.bridge.cv2_to_imgmsg(gray, encoding='mono8')
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = 'camera_link'
        self.pub.publish(message)
        self.count += 1

    def report(self):
        self.get_logger().info('[CAMERA] %d frames, %.3f Hz (target %.1f)' % (self.count, self.count / (time.monotonic() - self.started), CAMERA_HZ))


def main():
    rclpy.init()
    node = CameraSim()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
