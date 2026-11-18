"""Existing chassis command adapter; emergency input adds no separate process."""
import math
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TwistStamped
from std_msgs.msg import Bool
from std_srvs.srv import Trigger


class ControlBridge(Node):
    def __init__(self):
        super().__init__('chassis_command_bridge')
        self.declare_parameter('minimum_turning_radius', 0.60)
        self.declare_parameter('max_speed', 0.8)
        self.last = 0
        self.command = Twist()
        self.estopped = False
        self.pub = self.create_publisher(TwistStamped, '/ackermann_steering_controller/reference', 1)
        self.enabled = self.create_publisher(Bool, '/controller_enabled', 1)
        self.create_subscription(Twist, '/cmd_vel', self.receive, 1)
        self.create_subscription(Bool, '/emergency_stop', self.emergency, 1)
        self.create_service(Trigger, '/clear_emergency_stop', self.clear)
        self.create_timer(0.05, self.tick)

    def receive(self, message):
        values = [message.linear.x, message.angular.z]
        if not all(math.isfinite(value) for value in values):
            return
        self.last = time.monotonic()
        self.command = message

    def emergency(self, message):
        if message.data:
            self.estopped = True
            self.command = Twist()
            self.tick()

    def clear(self, request, response):
        self.estopped = False
        self.command = Twist()
        self.last = 0
        response.success, response.message = True, 'Latch cleared manually; fresh velocity required'
        return response

    def tick(self):
        output = TwistStamped()
        output.header.stamp = self.get_clock().now().to_msg()
        if not self.estopped and time.monotonic()-self.last < 0.5:
            limit = self.get_parameter('max_speed').value
            speed = max(-limit, min(limit, self.command.linear.x))
            omega_limit = abs(speed)/self.get_parameter('minimum_turning_radius').value
            output.twist.linear.x = speed
            output.twist.angular.z = max(-omega_limit, min(omega_limit, self.command.angular.z))
        self.pub.publish(output)
        self.enabled.publish(Bool(data=not self.estopped))


def main():
    rclpy.init()
    node = ControlBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.estopped = True
        if rclpy.ok():
            node.tick()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
