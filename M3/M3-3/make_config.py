"""Generate reproducible Nav2 configurations from installed Humble snapshot."""
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parent


def main():
    data=yaml.safe_load((ROOT/'config/nav2_humble.original.yaml').read_text())
    notes=[]
    def set_value(path,value,reason):
        target=data; keys=path.split('/')
        for key in keys[:-1]: target=target.setdefault(key,{})
        old=target.get(keys[-1],'<not in defaults>'); target[keys[-1]]=value
        notes.append(dict(parameter=path,old=old,new=value,reason=reason))
    def node(name,key,value,reason): set_value(name+'/ros__parameters/'+key,value,reason)
    node('amcl','laser_max_range',8.,'Match physical simulated laser range')
    node('amcl','laser_min_range',.12,'Reject below laser minimum')
    node('amcl','set_initial_pose',True,'Known surveyed start; never read Gazebo truth for localization')
    node('amcl','initial_pose',dict(x=0.,y=0.,z=0.,yaw=0.),'Map start at world (1,1)')
    node('amcl','update_min_d',.1,'Dense updates through 1m gate')
    node('amcl','update_min_a',.1,'Car turning updates')
    node('amcl','max_particles',1000,'Bound VM CPU')
    node('amcl','min_particles',300,'Bound VM CPU')
    node('amcl','sigma_hit',.05,'Laser sigma .01m; include grid uncertainty')
    # Differential odometry proposal is used for forward car motion, not a differential command model.
    node('bt_navigator','robot_base_frame','base_footprint','Ground projection for planar navigation')
    node('bt_navigator','default_nav_to_pose_bt_xml',str(ROOT/'config/car_navigation.xml'),'Recovery excludes impossible in-place spin')
    through=(ROOT/'config/car_navigation.xml').read_text().replace('<ComputePathToPose goal="{goal}"','<ComputePathThroughPoses goals="{goals}"')
    (ROOT/'config/car_through_poses.xml').write_text(through)
    node('bt_navigator','default_nav_through_poses_bt_xml',str(ROOT/'config/car_through_poses.xml'),'Both navigator BTs must exclude unavailable spin action')
    node('controller_server','failure_tolerance',2.,'Allow one global replan before abort')
    node('controller_server','progress_checker/required_movement_radius',.15,'Slow approach still counts as progress')
    node('controller_server','progress_checker/movement_time_allowance',20.,'Wait for obstacle replan')
    node('controller_server','general_goal_checker/xy_goal_tolerance',.08,'Leave localization margin inside independent truth qualification <=.15m')
    node('controller_server','general_goal_checker/yaw_goal_tolerance',.15,'Tightened heading; independent truth qualification <=.20rad, without in-place rotation')
    node('controller_server','general_goal_checker/stateful',False,'Require position and heading together at completion')
    node('controller_server','general_goal_checker/plugin','smartcar_nav_checks::ValidPoseGoalChecker','Reject invalid transformed goal quaternion; prevents observed Humble premature success after TF failure')
    node('controller_server','FollowPath',{
        'plugin':'nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController',
        'desired_linear_vel':.32,'lookahead_dist':.5,'min_lookahead_dist':.30,'max_lookahead_dist':.65,
        'lookahead_time':1.2,'use_velocity_scaled_lookahead_dist':True,'transform_tolerance':.5,
        'min_approach_linear_velocity':.035,'approach_velocity_scaling_dist':.8,
        'use_collision_detection':True,'max_allowed_time_to_collision_up_to_carrot':2.0,
        'use_regulated_linear_velocity_scaling':True,'use_cost_regulated_linear_velocity_scaling':True,
        'regulated_linear_scaling_min_radius':.85,'regulated_linear_scaling_min_speed':.08,
        'cost_scaling_dist':.3,'cost_scaling_gain':1.,'inflation_cost_scaling_factor':3.,
        'use_rotate_to_heading':False,'allow_reversing':True,'max_angular_accel':1.0},'RPP supports planned reverse correction, no in-place turn; chassis clamps curvature to radius >=.60m')
    node('planner_server','expected_planner_frequency',1.,'Match 1Hz BT replan instead of default20')
    node('planner_server','GridBased',{
        'plugin':'nav2_smac_planner/SmacPlannerHybrid','tolerance':.25,'downsample_costmap':False,
        'allow_unknown':False,'max_iterations':1000000,'max_on_approach_iterations':1000,
        'max_planning_time':2.,'motion_model_for_search':'REEDS_SHEPP','angle_quantization_bins':72,
        'analytic_expansion_ratio':3.5,'analytic_expansion_max_length':3.,'minimum_turning_radius':.65,
        'reverse_penalty':2.,'change_penalty':0.,'non_straight_penalty':1.2,'cost_penalty':2.,
        'retrospective_penalty':.015,'lookup_table_size':20.,'cache_obstacle_heuristic':True,
        'smooth_path':True},'Hybrid-A* Reeds-Shepp plans forward/reverse Ackermann maneuvers with radius .65m')
    footprint='[[0.365,0.13],[0.365,-0.13],[-0.085,-0.13],[-0.085,0.13]]'
    for name in ['local_costmap','global_costmap']:
        prefix=name+'/'+name+'/ros__parameters/'
        for key,value,reason in [
            ('robot_base_frame','base_footprint','Rear-axle midpoint, matching controller kinematics'),('footprint',footprint,'Unchanged .45x.22m body centered .14m ahead; .26m envelope includes steered wheels'),
            ('footprint_padding',.08,'Planning margin for measured localization/grid/tracking error; evaluation retains physical envelope'),
            ('plugins',['obstacle_layer','inflation_layer'] if name=='local_costmap' else ['static_layer','obstacle_layer','inflation_layer'],'2D laser; avoid needless voxel projection'),
            ('inflation_layer/inflation_radius',.45,'Soft cost field encourages corner clearance while .95m gate remains traversable with padded footprint'),
            ('obstacle_layer',dict(plugin='nav2_costmap_2d::ObstacleLayer',enabled=True,observation_sources='scan',scan=dict(topic='/scan',max_obstacle_height=2.,clearing=True,marking=True,data_type='LaserScan',raytrace_max_range=8.,raytrace_min_range=.12,obstacle_max_range=7.8,obstacle_min_range=.12)),'Use actual 8m laser for obstacle marking/clearing')]: set_value(prefix+key,value,reason)
    set_value('local_costmap/local_costmap/ros__parameters/width',5,'See turn before entering it')
    set_value('local_costmap/local_costmap/ros__parameters/height',5,'See turn before entering it')
    node('velocity_smoother','max_velocity',[.5,0.,.9],'Compatible with selected car command envelope')
    node('velocity_smoother','min_velocity',[-.20,0.,-.9],'Allow bounded reverse commands consistently with planner and controller')
    node('velocity_smoother','max_accel',[.5,0.,1.],'Reduce tire slip on velocity changes')
    node('velocity_smoother','max_decel',[-.7,0.,-1.],'Controlled braking')
    node('behavior_server','behavior_plugins',['backup','drive_on_heading','wait'],'No spin behavior for car')
    comments=''.join('# '+n['parameter']+': '+n['reason']+'\n' for n in notes)
    (ROOT/'config/nav2_params.yaml').write_text(comments+yaml.safe_dump(data,sort_keys=False))
    (ROOT/'config/changes.yaml').write_text(yaml.safe_dump(notes,sort_keys=False))


if __name__=='__main__': main()
