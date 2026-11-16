import math
import time
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from gazebo_msgs.msg import ModelStates
from gazebo_msgs.srv import SetEntityState
from geometry_msgs.msg import Twist


def yaw(q):
    return math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))


def normalize(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


class SimulationClient(Node):
    def __init__(self, name='simulation_experiment'):
        super().__init__(name, parameter_overrides=[Parameter('use_sim_time', value=True)])
        self.odom = self.truth = None
        self.recording = False
        self.odom_rows, self.truth_rows = [], []
        self.command = Twist()
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 1)
        self.create_subscription(Odometry, '/odom', self.on_odom, qos_profile_sensor_data)
        self.create_subscription(ModelStates, '/gazebo/model_states', self.on_truth, qos_profile_sensor_data)
        self.create_timer(0.05, lambda: self.publisher.publish(self.command))

    def seconds(self):
        return self.get_clock().now().nanoseconds/1e9

    def row(self, pose):
        return [self.seconds(), pose.position.x, pose.position.y, yaw(pose.orientation)]

    def on_odom(self, message):
        self.odom = self.row(message.pose.pose)
        if self.recording:
            self.odom_rows.append(self.odom)

    def on_truth(self, message):
        if 'smart_car' in message.name:
            self.truth = self.row(message.pose[message.name.index('smart_car')])
            if self.recording:
                self.truth_rows.append(self.truth)

    def ready(self, wall_timeout=60):
        deadline = time.monotonic()+wall_timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.odom is not None and self.truth is not None and self.seconds() > 0:
                return
        raise RuntimeError('Missing /odom, /gazebo/model_states, or /clock: '+str(self.get_topic_names_and_types()))

    def advance(self, seconds):
        target = self.seconds()+seconds
        wall_deadline = time.monotonic()+max(30, seconds*30)
        while self.seconds() < target and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)
            if time.monotonic() >= wall_deadline:
                raise RuntimeError('Simulation clock stalled')

    def drive(self, speed, omega, seconds):
        self.command.linear.x, self.command.angular.z = float(speed), float(omega)
        self.advance(seconds)

    def reset_pose(self, x=0.0, y=0.0, heading=0.0):
        self.command = Twist()
        self.advance(0.5)
        client = self.create_client(SetEntityState, '/gazebo/set_entity_state')
        if not client.wait_for_service(timeout_sec=5):
            raise RuntimeError('/gazebo/set_entity_state unavailable')
        request = SetEntityState.Request()
        request.state.name = 'smart_car'
        request.state.reference_frame = 'world'
        request.state.pose.position.x, request.state.pose.position.y, request.state.pose.position.z = float(x), float(y), 0.065
        request.state.pose.orientation.z, request.state.pose.orientation.w = math.sin(heading/2), math.cos(heading/2)
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=10)
        assert future.done() and future.result().success
        self.destroy_client(client)
        self.advance(1.0)
