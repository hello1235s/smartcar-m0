"""Record this actual /map and TF application window during a SLAM survey."""
import argparse
import json
from pathlib import Path
import signal
import sys
import time
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy
from nav_msgs.msg import OccupancyGrid
from tf2_ros import Buffer,TransformListener,TransformException
from PyQt5 import QtCore,QtGui,QtWidgets

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    rclpy.init();node=Node('actual_slam_operation_view',parameter_overrides=[Parameter('use_sim_time',value=True)])
    buffer=Buffer();listener=TransformListener(buffer,node);app=QtWidgets.QApplication(sys.argv[:1])
    state=dict(map_messages=0,tf_poses=0,recorded_frames=0,source='/map and map->base_footprint TF',
               truth_input=False,first_map_sim_t=None,last_map_sim_t=None)
    current={};poses=[];started=time.monotonic();log=(out/'map_messages.jsonl').open('w')
    qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
    def receive(message):
        grid=np.asarray(message.data,dtype=np.int16).reshape(message.info.height,message.info.width)
        pixels=np.full(grid.shape,205,dtype=np.uint8);pixels[grid==0]=254;pixels[grid>0]=0
        pixels=np.ascontiguousarray(pixels[::-1,:]);image=QtGui.QImage(pixels.data,pixels.shape[1],pixels.shape[0],pixels.strides[0],QtGui.QImage.Format_Grayscale8).copy()
        current.update(image=image,width=message.info.width,height=message.info.height,resolution=message.info.resolution,
                       origin=(message.info.origin.position.x,message.info.origin.position.y))
        state['map_messages']+=1;state['last_map_sim_t']=node.get_clock().now().nanoseconds/1e9
        if state['first_map_sim_t'] is None:state['first_map_sim_t']=state['last_map_sim_t']
        log.write(json.dumps(dict(sim_t=state['last_map_sim_t'],width=message.info.width,height=message.info.height,
                                 occupied=int(np.count_nonzero(grid>0)),unknown=int(np.count_nonzero(grid<0))))+'\n');log.flush()
    node.create_subscription(OccupancyGrid,'/map',receive,qos)
    class Window(QtWidgets.QWidget):
        def paintEvent(self,event):
            painter=QtGui.QPainter(self);painter.fillRect(self.rect(),QtGui.QColor('#edf3f6'));painter.setPen(QtGui.QColor('#16364a'))
            painter.drawText(24,30,'ACTUAL SLAM OPERATION | live /map + TF | evaluation truth is not used')
            painter.drawText(24,55,'map updates=%d | TF poses=%d | ROS clock=%.2fs'%(state['map_messages'],state['tf_poses'],node.get_clock().now().nanoseconds/1e9))
            if current:
                image=current['image'];scale=min(940/image.width(),570/image.height())
                painter.drawImage(QtCore.QRectF(30,80,image.width()*scale,image.height()*scale),image)
                ox,oy=current['origin'];res=current['resolution']
                if len(poses)>1:
                    path=QtGui.QPainterPath()
                    for i,(x,y) in enumerate(poses):
                        px=30+(x-ox)/res*scale;py=80+(image.height()-(y-oy)/res)*scale
                        if i:path.lineTo(px,py)
                        else:path.moveTo(px,py)
                    painter.setPen(QtGui.QPen(QtGui.QColor('#e04f42'),2));painter.drawPath(path)
            else:painter.drawText(30,110,'Waiting for real SLAM map messages...')
            painter.setPen(QtGui.QColor('#16364a'));painter.drawText(24,680,'Gray: unknown | white: free | black: measured occupancy | red: estimated map-frame TF trajectory')
    window=Window();window.setFixedSize(1000,700);window.setWindowTitle('Actual SLAM operation recording');window.show()
    writer=cv2.VideoWriter(str(out/'actual_slam_operation.avi'),cv2.VideoWriter_fourcc(*'MJPG'),3,(1000,700))
    if not writer.isOpened():raise RuntimeError('SLAM application recording writer failed')
    def tick():
        for _ in range(24):rclpy.spin_once(node,timeout_sec=0)
        try:
            tf=buffer.lookup_transform('map','base_footprint',rclpy.time.Time());position=tf.transform.translation
            point=(position.x,position.y)
            if not poses or np.linalg.norm(np.asarray(point)-poses[-1])>.015:poses.append(point)
            state['tf_poses']+=1
        except TransformException:pass
        window.repaint()
        capture=window.grab().toImage().convertToFormat(QtGui.QImage.Format_RGBA8888)
        ptr=capture.bits();ptr.setsize(capture.byteCount());pixels=np.frombuffer(ptr,dtype=np.uint8).reshape(capture.height(),capture.width(),4)
        writer.write(cv2.cvtColor(pixels,cv2.COLOR_RGBA2BGR));state['recorded_frames']+=1
        if state['recorded_frames']%90==0:window.grab().save(str(out/('actual_map_%04d.png'%state['recorded_frames'])))
    timer=QtCore.QTimer();timer.timeout.connect(tick);timer.start(333)
    signal.signal(signal.SIGINT,lambda *_:app.quit());signal.signal(signal.SIGTERM,lambda *_:app.quit())
    try:app.exec_()
    finally:
        window.grab().save(str(out/'actual_slam_final.png'));writer.release();log.close()
        state.update(wall_seconds=time.monotonic()-started,estimated_trajectory=poses,
                     status='PASS' if state['map_messages']>=5 and len(poses)>10 and state['recorded_frames']>=30 else 'INCOMPLETE')
        (out/'recording.json').write_text(json.dumps(state,indent=2));node.destroy_node();rclpy.try_shutdown()

if __name__=='__main__':main()
