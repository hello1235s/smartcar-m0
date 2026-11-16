"""Pure pursuit of a known survey route using SLAM TF, never Gazebo truth."""
import argparse
import csv
import math
import time
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import Twist
from tf2_ros import Buffer, TransformListener, TransformException


def route():
    # World ring starts at (1,1). SLAM starts at map (0,0), heading east.
    points = []
    r = 0.75
    segments = [((0,0),(9.25,0)), ((10,0.75),(10,5.25)),
                ((9.25,6),(0.75,6)), ((0,5.25),(0,0.75)), ((0.75,0),(1.0,0))]
    arcs = [(9.25,.75,-math.pi/2), (9.25,5.25,0), (.75,5.25,math.pi/2), (.75,.75,math.pi)]
    for i, (start,end) in enumerate(segments):
        n = max(2, int(math.dist(start,end)/.05))
        points.extend([(start[0]+(end[0]-start[0])*t/n,start[1]+(end[1]-start[1])*t/n) for t in range(n)])
        if i < 4:
            cx,cy,a = arcs[i]
            points.extend([(cx+r*math.cos(a+t*math.pi/2/24),cy+r*math.sin(a+t*math.pi/2/24)) for t in range(24)])
    points.append((1,0))
    return points


def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',required=True); p.add_argument('--timeout',type=float,default=600)
    args=p.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    rclpy.init(); node=Node('survey_route',parameter_overrides=[Parameter('use_sim_time',value=True)])
    buffer=Buffer(); listener=TransformListener(buffer,node); pub=node.create_publisher(Twist,'/cmd_vel',1)
    points=route(); index=0; rows=[]; deadline=time.monotonic()+args.timeout; started=None
    try:
        while rclpy.ok() and time.monotonic()<deadline:
            rclpy.spin_once(node,timeout_sec=.05)
            try:
                tf=buffer.lookup_transform('map','base_footprint',rclpy.time.Time())
            except TransformException:
                continue
            if started is None: started=node.get_clock().now().nanoseconds/1e9
            x,y=tf.transform.translation.x,tf.transform.translation.y
            q=tf.transform.rotation; yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
            candidates=range(index,min(index+35,len(points)))
            index=min(candidates,key=lambda j:math.hypot(points[j][0]-x,points[j][1]-y))
            target=index
            while target<len(points)-1 and math.hypot(points[target][0]-x,points[target][1]-y)<.45: target+=1
            dx,dy=points[target][0]-x,points[target][1]-y
            curvature=max(-1/.60,min(1/.60,2*(-math.sin(yaw)*dx+math.cos(yaw)*dy)/max(.05,dx*dx+dy*dy)))
            speed=.13 if abs(curvature)>.35 else .25
            cmd=Twist(); cmd.linear.x=speed; cmd.angular.z=speed*curvature; pub.publish(cmd)
            rows.append([node.get_clock().now().nanoseconds/1e9,x,y,yaw,index,curvature])
            if index>=len(points)-6 and math.hypot(x-1,y)<.2:
                print('SURVEY_LOOP_COMPLETED',len(rows),flush=True); break
        else:
            raise TimeoutError('Survey incomplete at waypoint '+str(index)+'/'+str(len(points)))
    finally:
        for _ in range(5): pub.publish(Twist()); rclpy.spin_once(node,timeout_sec=.05)
        with (out/'slam_route.csv').open('w') as f:
            w=csv.writer(f); w.writerow(['t','map_x','map_y','yaw','waypoint','curvature']); w.writerows(rows)
        node.destroy_node(); rclpy.shutdown()


if __name__=='__main__': main()
