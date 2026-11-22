"""One command, two isolated instances of the same training launch."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    package=Path(get_package_share_directory('smartcar_training'))
    return LaunchDescription([
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(package/'launch/bringup.launch.py')),
            launch_arguments={'namespace':name,'params_file':str(package/'config'/('params_'+name+'.yaml'))}.items())
        for name in ['robot1','robot2']])
