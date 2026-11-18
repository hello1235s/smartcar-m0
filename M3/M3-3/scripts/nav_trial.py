import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry,Path as NavPath
from geometry_msgs.msg import Twist,TwistStamped
from gazebo_msgs.srv import SpawnEntity
from lifecycle_msgs.srv import GetState


def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',required=True); p.add_argument('--goal',default='10,4,1.5707963'); p.add_argument('--timeout',type=float,default=150)
    p.add_argument('--obstacle-at'); p.add_argument('--delay',type=float,default=3.); p.add_argument('--obstacle-size',type=float,default=.6); a=p.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True); rclpy.init(); node=Node('navigation_trial',parameter_overrides=[Parameter('use_sim_time',value=True)])
    trajectory=[]; steering=[]; plans=[]; obstacle=None
    def seconds(): return node.get_clock().now().nanoseconds/1e9
    def odom(m):
        q=m.pose.pose.orientation; trajectory.append([seconds(),m.pose.pose.position.x,m.pose.pose.position.y,math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))])
    def cmd(m): steering.append([seconds(),m.linear.x,m.angular.z,math.atan(.28*m.angular.z/m.linear.x) if abs(m.linear.x)>.01 else 0.])
    def plan(m): plans.append(dict(t=seconds(),wall_ns=time.time_ns(),points=[[p.pose.position.x,p.pose.position.y] for p in m.poses]))
    node.create_subscription(Odometry,'/odom',odom,qos_profile_sensor_data); node.create_subscription(TwistStamped,'/ackermann_steering_controller/reference',lambda m:cmd(m.twist),10); node.create_subscription(NavPath,'/plan',plan,10)
    action=ActionClient(node,NavigateToPose,'/navigate_to_pose'); deadline=time.monotonic()+90
    while not action.wait_for_server(timeout_sec=.5):
        rclpy.spin_once(node,timeout_sec=.05)
        if time.monotonic()>deadline: raise RuntimeError('Nav2 action unavailable')
    lifecycle=node.create_client(GetState,'/bt_navigator/get_state')
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        rclpy.spin_once(node,timeout_sec=.1)
        if not lifecycle.service_is_ready(): continue
        state=lifecycle.call_async(GetState.Request()); rclpy.spin_until_future_complete(node,state,timeout_sec=2)
        if state.done() and state.result().current_state.id==3: break
    else: raise RuntimeError('BT navigator never reached active lifecycle state')
    trajectory.clear(); steering.clear(); plans.clear(); x,y,heading=map(float,a.goal.split(','))
    goal=NavigateToPose.Goal(); goal.pose.header.frame_id='map'; goal.pose.header.stamp=node.get_clock().now().to_msg()
    goal.pose.pose.position.x=x; goal.pose.pose.position.y=y; goal.pose.pose.orientation.z=math.sin(heading/2); goal.pose.pose.orientation.w=math.cos(heading/2)
    future=action.send_goal_async(goal); rclpy.spin_until_future_complete(node,future,timeout_sec=15)
    if not future.done() or not future.result().accepted: raise RuntimeError('Navigation goal rejected')
    handle=future.result(); result=handle.get_result_async(); start=seconds(); wall_start=time.monotonic(); spawn_future=None; inject_time=None
    while not result.done() and seconds()-start<a.timeout and time.monotonic()-wall_start<a.timeout*8:
        rclpy.spin_once(node,timeout_sec=.05)
        if a.obstacle_at and inject_time is None and seconds()-start>=a.delay:
            client=node.create_client(SpawnEntity,'/spawn_entity')
            if not client.wait_for_service(timeout_sec=2): raise RuntimeError('Gazebo spawn unavailable')
            req=SpawnEntity.Request(); req.name='temporary_obstacle'; ox,oy=map(float,a.obstacle_at.split(',')); req.initial_pose.position.x=ox; req.initial_pose.position.y=oy; req.initial_pose.position.z=.5
            size=a.obstacle_size; req.xml='<sdf version="1.6"><model name="temporary_obstacle"><static>true</static><link name="body"><collision name="c"><geometry><box><size>%s %s 1</size></box></geometry></collision><visual name="v"><geometry><box><size>%s %s 1</size></box></geometry></visual></link></model></sdf>'%(size,size,size,size)
            spawn_future=client.call_async(req); inject_time=seconds()
        if spawn_future and spawn_future.done() and obstacle is None:
            obstacle=dict(success=spawn_future.result().success,status=spawn_future.result().status_message,sim_t=inject_time,world_xy=a.obstacle_at,size=a.obstacle_size)
            assert obstacle['success'],str(obstacle)
    status=result.result().status if result.done() else 0
    if not result.done():
        cancel=handle.cancel_goal_async(); rclpy.spin_until_future_complete(node,cancel,timeout_sec=5)
    elapsed=seconds()-start; length=sum(math.hypot(b[1]-a[1],b[2]-a[2]) for a,b in zip(trajectory,trajectory[1:]))
    smooth=sum(abs(b[3]-a[3]) for a,b in zip(steering,steering[1:]))/max(length,1e-6)
    report=dict(success=status==4,status=status,sim_seconds=elapsed,wall_seconds=time.monotonic()-wall_start,path_length_m=length,steering_variation_rad_per_m=smooth,plans=len(plans),obstacle=obstacle,first_plan_after_injection_delay_s=next((p['t']-inject_time for p in plans if inject_time and p['t']>=inject_time),None))
    for name,rows,header in [('trajectory',trajectory,['t','x','y','theta']),('commands',steering,['t','v','omega','steering'])]:
        with (out/(name+'.csv')).open('w') as f: w=csv.writer(f); w.writerow(header); w.writerows(rows)
    (out/'plans.json').write_text(json.dumps(plans)); (out/'result.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report),flush=True)
    node.destroy_node(); rclpy.shutdown()


if __name__=='__main__': main()
