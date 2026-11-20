"""Read-only, bounded ROS health probe for the selected experiment domain."""
import argparse
import json
import os
import time
import math
p=argparse.ArgumentParser(); p.add_argument('--domain',default='180'); p.add_argument('--seconds',type=float,default=4.); a=p.parse_args()
os.environ['ROS_DOMAIN_ID']=a.domain
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry,Path
from sensor_msgs.msg import LaserScan
from gazebo_msgs.msg import ModelStates
from tf2_ros import Buffer,TransformListener,TransformException
rclpy.init(); node=Node('smartcar_read_only_probe',parameter_overrides=[Parameter('use_sim_time',value=True)])
buffer=Buffer(); listener=TransformListener(buffer,node); counts=dict(scan=0,odom=0,plan=0); observations={}
def heading(q): return math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
def count(name):
    def receive(m): counts[name]+=1
    return receive
node.create_subscription(LaserScan,'/scan',count('scan'),qos_profile_sensor_data)
node.create_subscription(Odometry,'/odom',count('odom'),qos_profile_sensor_data)
def plan(m):
    counts['plan']+=1
    observations['plan_tail']=[[p.pose.position.x,p.pose.position.y,heading(p.pose.orientation)] for p in m.poses[-5:]]
def truth(m):
    if 'smart_car' in m.name:
        p=m.pose[m.name.index('smart_car')]; observations['world_pose']=[p.position.x,p.position.y,heading(p.orientation)]
node.create_subscription(Path,'/plan',plan,10)
node.create_subscription(ModelStates,'/gazebo/model_states',truth,qos_profile_sensor_data)
start=time.monotonic(); map_pose=None
try:
    while time.monotonic()-start<a.seconds:
        rclpy.spin_once(node,timeout_sec=.05)
        try:
            tf=buffer.lookup_transform('map','base_footprint',rclpy.time.Time())
            map_pose=[tf.transform.translation.x,tf.transform.translation.y,heading(tf.transform.rotation)]
        except TransformException: pass
    print(json.dumps(dict(domain=a.domain,wall_seconds=time.monotonic()-start,sim_clock=node.get_clock().now().nanoseconds/1e9,received=counts,map_position=map_pose,**observations)))
finally: node.destroy_node(); rclpy.shutdown()
