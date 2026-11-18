"""Same grayscale/brightness/contrast semantics, bounded queues, independent control."""
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.executors import MultiThreadedExecutor
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist


def enhance(gray):
    values = np.arange(256, dtype=np.int16)
    lut = np.clip((np.minimum(values + 20, 255) - 128) * 3 // 2 + 128, 0, 255).astype(np.uint8)
    large = cv2.resize(gray, (1280, 720), interpolation=cv2.INTER_LINEAR)
    return cv2.resize(cv2.LUT(large, lut), (640, 480), interpolation=cv2.INTER_LINEAR)


class ImageProc(Node):
    def __init__(self):
        super().__init__('image_proc')
        cv2.setNumThreads(1)
        self.bridge = CvBridge()
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.pub = self.create_publisher(Image, '/perception/result', qos)
        self.sub = self.create_subscription(Image, '/camera/image_raw', self.receive, qos)

    def receive(self, message):
        gray = self.bridge.imgmsg_to_cv2(message, desired_encoding='mono8')
        output = self.bridge.cv2_to_imgmsg(enhance(gray), encoding='mono8')
        output.header = message.header
        self.pub.publish(output)


class ControlLoop(Node):
    def __init__(self):
        super().__init__('control_loop')
        self.pub = self.create_publisher(Twist, '/control/cmd', 1)
        self.create_timer(1 / 21.0, self.tick)

    def tick(self):
        message = Twist()
        message.linear.x, message.angular.z = 0.1, 0.05
        self.pub.publish(message)


def main():
    rclpy.init()
    nodes = [ImageProc(), ControlLoop()]
    executor = MultiThreadedExecutor(num_threads=2)
    for node in nodes:
        executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        executor.shutdown()
        for node in nodes:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
