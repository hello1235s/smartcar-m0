import math
import time

import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import SetParametersResult
from rcl_interfaces.srv import GetParameters
from sensor_interfaces.msg import SensorData
from sensor_interfaces.srv import TriggerAlarm
from std_msgs.msg import Float32


class Sensor(Node):
    def __init__(self):
        super().__init__('node_a_sensor')
        self.sequence = 0
        self.pub = self.create_publisher(SensorData, 'sensor_data', 10)
        self.timer = self.create_timer(0.1, self.tick)

    def tick(self):
        self.sequence += 1
        message = SensorData()
        message.distance = 0.5 + 0.4 * math.sin(self.sequence * 0.12)
        message.unit = 'm'
        message.stamp = self.get_clock().now().to_msg()
        message.status = 1 if self.sequence % 40 == 0 else 0
        self.pub.publish(message)


class Filter(Node):
    def __init__(self):
        super().__init__('node_b_filter')
        self.declare_parameter('alpha', 0.3)
        self.declare_parameter('alarm_service_enabled', True)
        self.value = None
        self.pub = self.create_publisher(Float32, 'processed_distance', 10)
        self.sub = self.create_subscription(SensorData, 'sensor_data', self.receive, 10)
        self.server = self.create_service(TriggerAlarm, 'trigger_alarm', self.alarm)
        self.add_on_set_parameters_callback(self.change)

    def change(self, parameters):
        for p in parameters:
            if p.name == 'alpha' and (not isinstance(p.value, float) or not math.isfinite(p.value) or not 0 < p.value <= 1):
                return SetParametersResult(successful=False, reason='alpha must be a finite double in (0, 1]')
        for p in parameters:
            if p.name == 'alpha':
                self.get_logger().info('alpha updated to %.3f' % p.value)
            if p.name == 'alarm_service_enabled':
                if not p.value and self.server is not None:
                    self.destroy_service(self.server)
                    self.server = None
                elif p.value and self.server is None:
                    self.server = self.create_service(TriggerAlarm, 'trigger_alarm', self.alarm)
        return SetParametersResult(successful=True)

    def receive(self, message):
        if message.status != 0 or message.unit != 'm' or not math.isfinite(message.distance):
            self.get_logger().warning('invalid sensor sample ignored: status=%d' % message.status)
            return
        alpha = self.get_parameter('alpha').value
        self.value = message.distance if self.value is None else alpha * message.distance + (1 - alpha) * self.value
        self.pub.publish(Float32(data=self.value))
        self.get_logger().info('raw=%.4f filtered=%.4f alpha=%.2f' % (message.distance, self.value, alpha), throttle_duration_sec=1)

    def alarm(self, request, response):
        self.get_logger().warning('[ALARM] 距离过近！ distance=%.4f' % request.distance)
        response.success, response.message = True, 'alarm acknowledged'
        return response


class Alarm(Node):
    def __init__(self):
        super().__init__('node_c_alarm')
        for name, value in [('alarm_threshold', 0.3), ('service_timeout', 1.0)]:
            self.declare_parameter(name, value)
        self.distance = None
        self.pending = False
        self.future = None
        self.deadline = 0
        self.next_alarm = 0
        self.client = self.create_client(TriggerAlarm, 'trigger_alarm')
        self.sub = self.create_subscription(Float32, 'processed_distance', self.receive, 10)
        self.timer = self.create_timer(0.02, self.tick)

    def receive(self, message):
        self.distance = message.data

    def tick(self):
        now = time.monotonic()
        if self.pending:
            if self.future is not None and self.future.done():
                try:
                    self.get_logger().info('alarm result: %s' % self.future.result().message)
                except Exception as error:
                    self.get_logger().warning('alarm error: %s' % error)
                self.pending = False
            elif now >= self.deadline:
                if self.future is not None:
                    self.future.cancel()
                self.pending = False
                self.get_logger().warning('[WARN] 报警服务超时')
            return
        if self.distance is None or self.distance >= self.get_parameter('alarm_threshold').value or now < self.next_alarm:
            return
        self.pending = True
        self.deadline = now + self.get_parameter('service_timeout').value
        self.next_alarm = self.deadline + 0.25
        self.future = self.client.call_async(TriggerAlarm.Request(distance=self.distance)) if self.client.service_is_ready() else None


def run(cls):
    rclpy.init()
    node = cls()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def sensor_main():
    run(Sensor)


def filter_main():
    run(Filter)


def alarm_main():
    run(Alarm)


def ready_main():
    import sys
    rclpy.init()
    node = Node('filter_readiness_probe')
    service = node.create_client(GetParameters, 'node_b_filter/get_parameters')
    okay = False
    try:
        if service.wait_for_service(timeout_sec=15):
            future = service.call_async(GetParameters.Request(names=['alpha']))
            rclpy.spin_until_future_complete(node, future, timeout_sec=5)
            okay = future.done() and future.result() is not None and len(future.result().values) == 1
    finally:
        node.destroy_node()
        rclpy.shutdown()
    print('FILTER_READY' if okay else 'FILTER_READINESS_FAILED', flush=True)
    sys.exit(0 if okay else 2)
