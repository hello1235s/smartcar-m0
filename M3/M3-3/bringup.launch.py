from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,IncludeLaunchDescription,OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
import tempfile
import yaml
import atexit
import shutil
ROOT=Path(__file__).resolve().parent


def setup(context):
    description=Path(get_package_share_directory('smart_car_description'))
    nav=Path(get_package_share_directory('nav2_bringup'))
    original=Path(LaunchConfiguration('params_file').perform(context)).expanduser().resolve()
    if not original.is_file(): raise RuntimeError('Nav2 parameter file does not exist: '+str(original))
    settings=yaml.safe_load(original.read_text())
    bt=settings['bt_navigator']['ros__parameters']
    for key,filename in [('default_nav_to_pose_bt_xml','car_navigation.xml'),('default_nav_through_poses_bt_xml','car_through_poses.xml')]:
        path=ROOT/'config'/filename
        if not path.is_file(): raise RuntimeError('Missing Ackermann behavior tree: '+str(path))
        bt[key]=str(path)
    # Resolve paths per checkout without rewriting the supplied experiment config.
    runtime=Path(tempfile.mkdtemp(prefix='smartcar_nav2_'))/'nav2_params.yaml'
    runtime.write_text(yaml.safe_dump(settings,sort_keys=False))
    atexit.register(shutil.rmtree,runtime.parent,ignore_errors=True)
    return [IncludeLaunchDescription(PythonLaunchDescriptionSource(str(description/'launch/sim.launch.py')),launch_arguments={'world':str(ROOT.parent/'M3-2/worlds/scene.world'),'x':'1.0','y':'1.0','physics_seed':LaunchConfiguration('physics_seed').perform(context)}.items()),
            IncludeLaunchDescription(PythonLaunchDescriptionSource(str(nav/'launch/bringup_launch.py')),launch_arguments={'map':str(ROOT.parent/'M3-2/maps/map.yaml'),'use_sim_time':'true','params_file':str(runtime),'autostart':'true','use_composition':'False'}.items())]


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('params_file',default_value=str(ROOT/'config/nav2_params.yaml')),DeclareLaunchArgument('physics_seed',default_value='42'),OpaqueFunction(function=setup)])
