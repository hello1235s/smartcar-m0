"""Measured Nav2 trial: ground truth is evaluation-only, never a control input."""
import argparse
import csv
import json
import math
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'common'))
from evaluation import footprint,clearance,rectangle,scene_obstacles,world_goal,goal_errors,point_segment_distance
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data
from nav2_msgs.action import NavigateToPose
from nav2_msgs.msg import BehaviorTreeLog
from nav_msgs.msg import Odometry,Path as NavPath,OccupancyGrid
from geometry_msgs.msg import TwistStamped
from gazebo_msgs.msg import ModelStates
from gazebo_msgs.srv import SpawnEntity
from lifecycle_msgs.srv import GetState
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer,TransformListener,TransformException


def yaw(q): return math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True); p.add_argument('--goal',default='10,4,1.5707963267948966')
    p.add_argument('--timeout',type=float,default=150.); p.add_argument('--obstacle-at')
    p.add_argument('--delay',type=float,default=3.); p.add_argument('--obstacle-size',type=float,default=.6)
    p.add_argument('--world-origin',default='1,1,0'); p.add_argument('--rear-reference',choices=['true','false'],default='true')
    p.add_argument('--position-limit',type=float,default=.15); p.add_argument('--yaw-limit',type=float,default=.20)
    p.add_argument('--minimum-path-length',type=float,default=5.)
    a=p.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    if (out/'result.json').exists(): p.error('Output already contains a trial; choose a new directory to preserve results')
    goal=tuple(map(float,a.goal.split(','))); origin=tuple(map(float,a.world_origin.split(',')))
    if len(goal)!=3 or len(origin)!=3: p.error('goal and world-origin require x,y,yaw')
    if not all(math.isfinite(v) for v in goal+origin): p.error('goal/origin must be finite')
    if min(a.timeout,a.obstacle_size,a.position_limit,a.yaw_limit)<=0 or a.delay<0: p.error('timeouts, dimensions and tolerances must be positive; delay cannot be negative')
    rclpy.init(); node=Node('navigation_trial',parameter_overrides=[Parameter('use_sim_time',value=True)])
    buffer=Buffer(); listener=TransformListener(buffer,node)
    trajectory=[]; commands=[]; plans=[]; truth=[]; estimates=[]; scan_times=[]; events=[]; measured_speeds=[]; costmaps={}
    def seconds(): return node.get_clock().now().nanoseconds/1e9
    def odom(m):
        trajectory.append([seconds(),m.pose.pose.position.x,m.pose.pose.position.y,yaw(m.pose.pose.orientation)])
        measured_speeds.append([seconds(),m.twist.twist.linear.x,m.twist.twist.angular.z])
    def cmd(m):
        v,w=m.twist.linear.x,m.twist.angular.z
        commands.append([seconds(),v,w,math.atan(.28*w/v) if abs(v)>.005 else 0.])
    def plan(m): plans.append(dict(t=seconds(),wall_ns=time.time_ns(),points=[[x.pose.position.x,x.pose.position.y] for x in m.poses]))
    def ground_truth(m):
        if 'smart_car' in m.name:
            pose=m.pose[m.name.index('smart_car')]; truth.append([seconds(),pose.position.x,pose.position.y,yaw(pose.orientation)])
    node.create_subscription(Odometry,'/odom',odom,qos_profile_sensor_data)
    node.create_subscription(TwistStamped,'/ackermann_steering_controller/reference',cmd,10)
    node.create_subscription(NavPath,'/plan',plan,10)
    node.create_subscription(ModelStates,'/gazebo/model_states',ground_truth,qos_profile_sensor_data)
    node.create_subscription(LaserScan,'/scan',lambda m:scan_times.append(seconds()),qos_profile_sensor_data)
    def behavior_log(message):
        # Event timestamps inside Humble's BT logger use another clock; receipt is ROS sim time.
        for event in message.event_log:
            events.append(dict(received_sim_t=seconds(),node=event.node_name,previous=event.previous_status,current=event.current_status))
    node.create_subscription(BehaviorTreeLog,'/behavior_tree_log',behavior_log,100)
    def costmap(message,label):
        previous=costmaps.get(label,{})
        if seconds()-previous.get('t',-100)<5: return
        costmaps[label]=dict(t=seconds(),frame=message.header.frame_id,resolution=message.info.resolution,
                             width=message.info.width,height=message.info.height,
                             origin=[message.info.origin.position.x,message.info.origin.position.y],data=list(message.data))
    for label in ['global','local']:
        node.create_subscription(OccupancyGrid,'/'+label+'_costmap/costmap',lambda m,label=label:costmap(m,label),10)
    def spin():
        rclpy.spin_once(node,timeout_sec=.05)
        try:
            tf=buffer.lookup_transform('map','base_footprint',rclpy.time.Time())
            estimates.append([seconds(),tf.transform.translation.x,tf.transform.translation.y,yaw(tf.transform.rotation)])
        except TransformException: pass
    action=ActionClient(node,NavigateToPose,'/navigate_to_pose')
    handle=result=None; accepted=False; obstacle=None; injection=None; spawn=None
    start=None; action_end=None; wall_start=time.monotonic(); failure=None; status=None
    try:
        deadline=time.monotonic()+90
        while not action.wait_for_server(timeout_sec=.25):
            spin()
            if time.monotonic()>deadline: raise RuntimeError('Nav2 action unavailable during initialization')
        lifecycle=node.create_client(GetState,'/bt_navigator/get_state'); deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            spin()
            if not lifecycle.service_is_ready(): continue
            state=lifecycle.call_async(GetState.Request()); rclpy.spin_until_future_complete(node,state,timeout_sec=2)
            if state.done() and state.result().current_state.id==3: break
        else: raise RuntimeError('BT navigator failed to become active')
        message=NavigateToPose.Goal(); message.pose.header.frame_id='map'; message.pose.header.stamp=node.get_clock().now().to_msg()
        message.pose.pose.position.x,message.pose.pose.position.y=goal[:2]
        message.pose.pose.orientation.z,message.pose.pose.orientation.w=math.sin(goal[2]/2),math.cos(goal[2]/2)
        future=action.send_goal_async(message); rclpy.spin_until_future_complete(node,future,timeout_sec=15)
        if not future.done() or not future.result().accepted: raise RuntimeError('Navigation target rejected')
        handle=future.result(); result=handle.get_result_async(); accepted=True
        trajectory.clear(); commands.clear(); plans.clear(); truth.clear(); estimates.clear(); scan_times.clear(); events.clear(); measured_speeds.clear()
        start=seconds(); wall_start=time.monotonic()
        print('NAV_TARGET_ACCEPTED '+json.dumps(dict(goal_map=goal,world_goal_for_evaluation=world_goal(goal,origin))),flush=True)
        while not result.done() and seconds()-start<a.timeout and time.monotonic()-wall_start<a.timeout*8:
            spin()
            if a.obstacle_at and injection is None and seconds()-start>=a.delay:
                client=node.create_client(SpawnEntity,'/spawn_entity')
                if not client.wait_for_service(timeout_sec=2): raise RuntimeError('Gazebo spawn service unavailable')
                request=SpawnEntity.Request(); request.name='temporary_obstacle'
                ox,oy=map(float,a.obstacle_at.split(',')); size=a.obstacle_size
                request.initial_pose.position.x,request.initial_pose.position.y,request.initial_pose.position.z=ox,oy,.5
                request.xml='<sdf version="1.6"><model name="temporary_obstacle"><static>true</static><link name="body"><collision name="c"><geometry><box><size>%s %s 1</size></box></geometry></collision><visual name="v"><geometry><box><size>%s %s 1</size></box></geometry></visual></link></model></sdf>'%(size,size,size,size)
                spawn=client.call_async(request); injection=seconds()
            if spawn and spawn.done() and obstacle is None:
                obstacle=dict(success=spawn.result().success,status=spawn.result().status_message,sim_t=injection,confirmed_sim_t=seconds(),world_xy=a.obstacle_at,size=a.obstacle_size)
                print('DYNAMIC_OBSTACLE_INSERTED '+json.dumps(obstacle),flush=True)
                if not obstacle['success']: raise RuntimeError('Obstacle injection failed')
        if result.done(): status=result.result().status
        else:
            failure='simulation_timeout' if seconds()-start>=a.timeout else 'wall_clock_watchdog'
            cancel=handle.cancel_goal_async(); rclpy.spin_until_future_complete(node,cancel,timeout_sec=5)
        action_end=seconds()
        settle=seconds()+.75; settle_wall=time.monotonic()+8
        while seconds()<settle and time.monotonic()<settle_wall: spin()
    except Exception as error:
        failure=str(error)
        if handle is not None:
            try: rclpy.spin_until_future_complete(node,handle.cancel_goal_async(),timeout_sec=3)
            except Exception: pass
    finally:
        elapsed=(action_end if action_end is not None else seconds())-start if start is not None else None
        odom_length=sum(math.hypot(b[1]-x[1],b[2]-x[2]) for x,b in zip(trajectory,trajectory[1:]))
        length=sum(math.hypot(b[1]-x[1],b[2]-x[2]) for x,b in zip(truth,truth[1:]))
        variation=sum(abs(b[3]-x[3]) for x,b in zip(commands,commands[1:]))/max(length,1e-6)
        reference_goal=world_goal(goal,origin)
        truth_error=goal_errors(truth[-1][1:],reference_goal) if truth else None
        estimate_error=goal_errors(estimates[-1][1:],goal) if estimates else None
        obstacles=scene_obstacles(); safety=[]
        for row in truth:
            active=list(obstacles)
            if obstacle and obstacle['success'] and row[0]>=obstacle['confirmed_sim_t']:
                ox,oy=map(float,a.obstacle_at.split(',')); active.append(('temporary_obstacle',rectangle(ox,oy,a.obstacle_size,a.obstacle_size)))
            poly=footprint(row[1:],a.rear_reference=='true')
            name,gap=min(((name,clearance(poly,shape)) for name,shape in active),key=lambda item:item[1])
            safety.append([row[0],gap,name])
        minimum=min((row[1] for row in safety),default=None)
        reasons=[]
        if status!=4: reasons.append(failure or 'navigation_action_status_'+str(status))
        if not truth_error: reasons.append('missing_independent_world_pose')
        else:
            if truth_error['position_m']>a.position_limit: reasons.append('world_position_error_exceeds_limit')
            if truth_error['yaw_rad']>a.yaw_limit: reasons.append('world_heading_error_exceeds_limit')
        if not safety or minimum<-.002: reasons.append('geometric_envelope_overlap_or_missing_samples')
        if length<a.minimum_path_length: reasons.append('insufficient_route_length')
        if len(scan_times)<10: reasons.append('insufficient_laser_observations')
        if a.obstacle_at and not (obstacle and obstacle['success']): reasons.append('required_obstacle_not_inserted')
        max_gap=max((b[0]-x[0] for x,b in zip(truth,truth[1:])),default=None)
        if max_gap is None or max_gap>.5: reasons.append('independent_pose_sampling_gap')
        if truth and seconds()-truth[-1][0]>.5: reasons.append('stale_final_independent_pose')
        distance_to_initial_path=None
        if a.obstacle_at and plans:
            center=tuple(map(float,a.obstacle_at.split(',')))
            initial=[world_goal((x,y,0.),origin)[:2] for x,y in plans[0]['points']]
            distance_to_initial_path=min((point_segment_distance(center,x,y) for x,y in zip(initial,initial[1:])),default=None)
        failure_replans=[]
        for event in events:
            if event['current']=='FAILURE' and event['node']=='FollowPath':
                subsequent=next((row for row in plans if row['t']>=event['received_sim_t']),None)
                failure_replans.append(dict(failure_received_sim_t=event['received_sim_t'],next_plan_delay_s=subsequent['t']-event['received_sim_t'] if subsequent else None))
        report=dict(success=not reasons,action_success=status==4,status=status,goal_accepted=accepted,failure_reason=failure,
                    qualification_failures=reasons,goal_map=goal,world_goal_for_evaluation=reference_goal,map_world_origin=origin,
                    endpoint_error_world_truth=truth_error,endpoint_error_map_estimate=estimate_error,
                    truth_pose_final=truth[-1][1:] if truth else None,estimated_pose_final=estimates[-1][1:] if estimates else None,
                    qualification_thresholds=dict(position_m=a.position_limit,yaw_rad=a.yaw_limit,minimum_path_m=a.minimum_path_length),
                    minimum_geometric_clearance_m=minimum,geometric_overlap_samples=sum(row[1]<-.002 for row in safety),
                    collision_metric='Independent world-pose polygon overlap with known world boxes; not a Gazebo contact sensor',
                    truth_is_evaluation_only=True,sim_seconds=elapsed,post_action_settle_seconds=seconds()-action_end if action_end is not None else None,wall_seconds=time.monotonic()-wall_start,
                    maximum_truth_sample_gap_s=max_gap,
                    path_length_m=length,path_length_source='world truth integral, evaluation only',odom_path_length_m=odom_length,
                    steering_variation_rad_per_m=variation,steering_source='Ackermann bridge reference command',plans=len(plans),obstacle=obstacle,
                    final_measured_speed=measured_speeds[-1][1:] if measured_speeds else None,
                    obstacle_distance_to_initial_path_m=distance_to_initial_path,
                    controller_failure_replans=failure_replans,
                    laser_samples=len(scan_times),first_plan_after_injection_delay_s=next((r['t']-injection for r in plans if injection is not None and r['t']>=injection),None))
        for name,rows,header in [('trajectory',trajectory,['t','x','y','theta']),('commands',commands,['t','v','omega','steering']),
                                 ('world_truth',truth,['t','world_x','world_y','yaw']),('map_estimate',estimates,['t','map_x','map_y','yaw']),
                                 ('geometric_clearance',safety,['t','clearance_m','closest_obstacle'])]:
            with (out/(name+'.csv')).open('w',newline='') as stream:
                writer=csv.writer(stream); writer.writerow(header); writer.writerows(rows)
        (out/'plans.json').write_text(json.dumps(plans))
        (out/'behavior_events.json').write_text(json.dumps(events,indent=2))
        (out/'costmaps.json').write_text(json.dumps(costmaps))
        (out/'result.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report),flush=True)
        node.destroy_node(); rclpy.shutdown()


if __name__=='__main__': main()
