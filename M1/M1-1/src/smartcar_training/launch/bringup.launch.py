from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler, EmitEvent, LogInfo
from launch.event_handlers import OnProcessStart, OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def configure(context):
    namespace = LaunchConfiguration('namespace').perform(context)
    requested = LaunchConfiguration('params_file').perform(context)
    path = Path(requested) if requested else Path(get_package_share_directory('smartcar_training')) / 'config' / 'params_robot1.yaml'
    if not path.is_file():
        return [LogInfo(msg='[ERROR] Parameter YAML file does not exist: ' + str(path)), EmitEvent(event=Shutdown(reason='invalid params_file'))]
    simulation = LaunchConfiguration('use_sim_time').perform(context).lower() == 'true'
    common = dict(package='smartcar_training', namespace=namespace, output='screen', parameters=[str(path), {'use_sim_time': simulation}])
    sensor = Node(executable='node_a_sensor', name='node_a_sensor', **common)
    filtering = Node(executable='node_b_filter', name='node_b_filter', **common)
    alarm = Node(executable='node_c_alarm', name='node_c_alarm', **common)
    gate = Node(package='smartcar_training', executable='filter_ready', namespace=namespace, output='screen')

    def after_probe(event, context):
        return [alarm] if event.returncode == 0 else [LogInfo(msg='[ERROR] Filter did not become ready'), EmitEvent(event=Shutdown(reason='filter readiness failed'))]
    return [RegisterEventHandler(OnProcessStart(target_action=filtering, on_start=[gate])),
            RegisterEventHandler(OnProcessExit(target_action=gate, on_exit=after_probe)), sensor, filtering]


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('namespace', default_value='robot1'),
                              DeclareLaunchArgument('params_file', default_value=''),
                              DeclareLaunchArgument('use_sim_time', default_value='false'),
                              OpaqueFunction(function=configure)])
