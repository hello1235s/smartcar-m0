from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro


def configure(context):
    root = Path(get_package_share_directory('smart_car_description'))
    camera = LaunchConfiguration('camera').perform(context)
    world = LaunchConfiguration('world').perform(context) or str(root/'worlds/square.world')
    description = xacro.process_file(str(root/'urdf/smart_car.urdf.xacro'), mappings={'enable_camera': camera}).toxml()
    publisher = Node(package='robot_state_publisher', executable='robot_state_publisher', parameters=[{'robot_description': description, 'use_sim_time': True}], output='screen')
    from launch.actions import ExecuteProcess
    server = ExecuteProcess(cmd=['gzserver','--verbose',world,'-s','libgazebo_ros_init.so','-s','libgazebo_ros_factory.so'], output='screen')
    spawn = Node(package='gazebo_ros', executable='spawn_entity.py', arguments=['-entity','smart_car','-topic','robot_description','-x',LaunchConfiguration('x'),'-y',LaunchConfiguration('y'),'-z','0.065','-timeout','60'], output='screen')
    joints = Node(package='controller_manager', executable='spawner', arguments=['joint_state_broadcaster','--controller-manager-timeout','60'], output='screen')
    steering = Node(package='controller_manager', executable='spawner', arguments=['ackermann_steering_controller','--controller-manager-timeout','60'], output='screen')
    bridge = Node(package='smartcar_training', executable='control_bridge', parameters=[{'use_sim_time': True}], output='screen')
    return [publisher, server, bridge,
            RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=[joints])),
            RegisterEventHandler(OnProcessExit(target_action=joints, on_exit=[steering])), spawn]


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('world', default_value=''), DeclareLaunchArgument('camera', default_value='false'),
                              DeclareLaunchArgument('x', default_value='0.0'), DeclareLaunchArgument('y', default_value='0.0'), OpaqueFunction(function=configure)])
