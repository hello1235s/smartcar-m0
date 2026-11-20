"""Offscreen Qt application captures actual ROS map, plan and laser, not a synthetic scene."""
import argparse
import math
import sys
import signal
import json
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data,QoSProfile,DurabilityPolicy,ReliabilityPolicy
from nav_msgs.msg import Path as NavPath,OccupancyGrid
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer,TransformListener,TransformException
import yaml
from PyQt5.QtWidgets import QApplication,QWidget
from PyQt5.QtGui import QPainter,QImage,QColor,QPen
from PyQt5.QtCore import QTimer,Qt


class View(QWidget):
    def __init__(self,root,out,obstacle=(8.,1.6),size=.6):
        super().__init__(); self.resize(900,650); self.setWindowTitle('Smartcar actual ROS navigation')
        self.costmaps={}; self.costmap_mode=False; self.captured_costmaps=set()
        self.stats=dict(ticks=0,scan_messages=0,laser_transform_success=0,laser_transform_missing=0)
        self.node=Node('actual_navigation_view',parameter_overrides=[Parameter('use_sim_time',value=True)])
        self.buffer=Buffer(); self.listener=TransformListener(self.buffer,self.node); self.path=[]; self.scan=None; self.pose=None; self.laser_pose=None; self.trajectory=[]; self.out=out; self.stage=0; self.obstacle=(obstacle[0]-1,obstacle[1]-1); self.obstacle_half=size/2
        config=yaml.safe_load((root/'M3/M3-2/maps/map.yaml').read_text()); self.origin=config['origin']; self.resolution=config['resolution']; self.map=QImage(str(root/'M3/M3-2/maps'/config['image']))
        self.node.create_subscription(NavPath,'/plan',lambda m:setattr(self,'path',[(p.pose.position.x,p.pose.position.y) for p in m.poses]),10)
        def scan(message): self.scan=message; self.stats['scan_messages']+=1
        self.node.create_subscription(LaserScan,'/scan',scan,qos_profile_sensor_data)
        map_qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
        for label in ['global','local']:
            self.node.create_subscription(OccupancyGrid,'/'+label+'_costmap/costmap',lambda m,label=label:self.receive_costmap(m,label),map_qos)
        self.timer=QTimer(); self.timer.timeout.connect(self.tick); self.timer.start(50)
    def receive_costmap(self,message,label):
        width,height=message.info.width,message.info.height
        if width<1 or height<1 or len(message.data)!=width*height: return
        stride=(width+3)//4*4; pixels=bytearray(stride*height)
        for row in range(height):
            data=message.data[(height-row-1)*width:(height-row)*width]
            pixels[row*stride:row*stride+width]=bytes(value+1 for value in data)
        image=QImage(bytes(pixels),width,height,stride,QImage.Format_Indexed8).copy()
        palette=[QColor('#959da3').rgb(),QColor('white').rgb()]
        palette.extend(QColor.fromHsvF((60-value*.6)/360,.75,.98).rgb() for value in range(1,100))
        palette.append(QColor('black').rgb()); image.setColorTable(palette)
        self.costmaps[label]=(image,message.header.frame_id,message.info.origin.position.x,message.info.origin.position.y,message.info.resolution)
    def save_status(self):
        (self.out/'viewer_status.json').write_text(json.dumps(dict(**self.stats,captured_navigation_stages=self.stage,costmap_topics=list(self.costmaps)),indent=2))
    def capture_costmaps(self,label):
        if len(self.costmaps)!=2 or label in self.captured_costmaps: return
        previous=self.costmap_mode; self.costmap_mode=True; self.repaint()
        self.grab().save(str(self.out/('actual_costmaps_'+label+'.png')))
        self.costmap_mode=previous; self.captured_costmaps.add(label); self.repaint(); self.save_status()
    def keyPressEvent(self,event):
        if event.key()==Qt.Key_C: self.costmap_mode=not self.costmap_mode; self.update()
        else: super().keyPressEvent(event)
    def project(self,x,y):
        return 40+(x-self.origin[0])/self.resolution*3,70+(self.map.height()-(y-self.origin[1])/self.resolution)*3
    def tick(self):
        # A single callback per tick let 50Hz TF backlog grow behind current scans.
        # Drain enough ready callbacks to keep stamped laser transforms available.
        for _ in range(24): rclpy.spin_once(self.node,timeout_sec=0)
        self.stats['ticks']+=1
        try:
            t=self.buffer.lookup_transform('map','base_footprint',rclpy.time.Time()); q=t.transform.rotation
            self.pose=(t.transform.translation.x,t.transform.translation.y,math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z)))
            self.trajectory.append(self.pose); self.update()
            self.laser_pose=None
            if self.scan:
                try:
                    laser=self.buffer.lookup_transform('map',self.scan.header.frame_id,rclpy.time.Time.from_msg(self.scan.header.stamp))
                    ql=laser.transform.rotation
                    self.laser_pose=(laser.transform.translation.x,laser.transform.translation.y,math.atan2(2*(ql.w*ql.z+ql.x*ql.y),1-2*(ql.y*ql.y+ql.z*ql.z)))
                    self.stats['laser_transform_success']+=1
                except TransformException: self.stats['laser_transform_missing']+=1
            hit=False
            if self.scan and self.laser_pose:
                x,y,yaw=self.laser_pose
                for i,r in enumerate(self.scan.ranges):
                    if not math.isfinite(r): continue
                    angle=yaw+self.scan.angle_min+i*self.scan.angle_increment; xx=x+r*math.cos(angle); yy=y+r*math.sin(angle)
                    if abs(xx-self.obstacle[0])<self.obstacle_half+.08 and abs(yy-self.obstacle[1])<self.obstacle_half+.08: hit=True; break
            conditions=[self.pose[0]>.1,hit,self.pose[0]>self.obstacle[0]-.3,self.pose[0]>self.obstacle[0]+self.obstacle_half+.4]
            if self.stage<4 and conditions[self.stage]:
                self.repaint(); self.grab().save(str(self.out/('actual_view_%d.png'%(self.stage+1)))); self.stage+=1
                self.save_status()
            if self.pose[0]>.1: self.capture_costmaps('start')
            if self.stage>=3: self.capture_costmaps('obstacle')
        except TransformException: pass
    def paintEvent(self,event):
        p=QPainter(self); p.fillRect(self.rect(),QColor('#10202b')); p.setPen(QColor('#e4eef4'))
        if self.costmap_mode:
            p.drawText(30,30,'ACTUAL ROS COSTMAPS | raw OccupancyGrid topics | C: navigation view')
            for column,label in enumerate(['global','local']):
                if label not in self.costmaps: continue
                image,frame,x,y,resolution=self.costmaps[label]; left=30+column*440
                p.drawText(left,65,'%s | frame=%s | resolution=%.2f m'%(label,frame,resolution))
                p.drawText(left,85,'origin=(%.2f, %.2f)'%(x,y))
                p.drawImage(left,105,image.scaled(400,440,Qt.KeepAspectRatio,Qt.FastTransformation))
            p.drawText(30,600,'White: free | warm colors: increasing cost | black: lethal | gray: unknown')
            p.end(); return
        p.drawText(30,30,'ACTUAL ROS VIEW | map + /plan + /scan + map→base TF | %.2f s'%(self.node.get_clock().now().nanoseconds/1e9))
        p.drawText(30,620,'C: live global/local costmaps | orange: TF trajectory | blue: plan | red: actual laser')
        p.drawImage(40,70,self.map.scaled(self.map.width()*3,self.map.height()*3,Qt.IgnoreAspectRatio,Qt.FastTransformation))
        for points,color in [(self.path,'#3d75d3'),([(x,y) for x,y,_ in self.trajectory],'#ed783d')]:
            p.setPen(QPen(QColor(color),2))
            for a,b in zip(points,points[1:]):
                x1,y1=self.project(*a); x2,y2=self.project(*b); p.drawLine(int(x1),int(y1),int(x2),int(y2))
        if self.pose:
            x,y,yaw=self.pose; px,py=self.project(x,y); p.setBrush(QColor('#23b38c')); p.setPen(QColor('#23b38c')); p.drawEllipse(int(px)-5,int(py)-5,10,10)
            p.drawLine(int(px),int(py),int(px+20*math.cos(yaw)),int(py-20*math.sin(yaw)))
            if self.scan and self.laser_pose:
                x,y,yaw=self.laser_pose
                p.setPen(QColor('#da424d'))
                for i,r in enumerate(self.scan.ranges):
                    if math.isfinite(r) and self.scan.range_min<r<self.scan.range_max:
                        angle=yaw+self.scan.angle_min+i*self.scan.angle_increment; sx,sy=self.project(x+r*math.cos(angle),y+r*math.sin(angle)); p.drawPoint(int(sx),int(sy))
        p.end()


def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',required=True); p.add_argument('--obstacle-at',default='8.0,1.6'); p.add_argument('--obstacle-size',type=float,default=.6); p.add_argument('--seconds',type=float); a=p.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True); root=Path(__file__).resolve().parents[3]
    rclpy.init(); app=QApplication(sys.argv); signal.signal(signal.SIGTERM,lambda *args:app.quit()); signal.signal(signal.SIGINT,lambda *args:app.quit()); view=View(root,out,tuple(map(float,a.obstacle_at.split(','))),a.obstacle_size); view.show()
    if a.seconds: QTimer.singleShot(int(a.seconds*1000),app.quit)
    try: app.exec_()
    finally: view.save_status(); view.node.destroy_node(); rclpy.try_shutdown()


if __name__=='__main__': main()
