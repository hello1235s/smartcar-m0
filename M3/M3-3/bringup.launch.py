from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,IncludeLaunchDescription,OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
ROOT=Path(__file__).resolve().parent


def setup(context):
    description=Path(get_package_share_directory('smart_car_description'))
    nav=Path(get_package_share_directory('nav2_bringup'))
    return [IncludeLaunchDescription(PythonLaunchDescriptionSource(str(description/'launch/sim.launch.py')),launch_arguments={'world':str(ROOT.parent/'M3-2/worlds/scene.world'),'x':'1.0','y':'1.0'}.items()),
            IncludeLaunchDescription(PythonLaunchDescriptionSource(str(nav/'launch/bringup_launch.py')),launch_arguments={'map':str(ROOT.parent/'M3-2/maps/map.yaml'),'use_sim_time':'true','params_file':LaunchConfiguration('params_file').perform(context),'autostart':'true','use_composition':'False'}.items())]


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('params_file',default_value=str(ROOT/'config/nav2_params.yaml')),OpaqueFunction(function=setup)])
