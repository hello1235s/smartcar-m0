"""Check saved projections against bag pixels and an independent rigid transform."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import cv2
import numpy as np
import yaml
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Image,LaserScan
from cv_bridge import CvBridge
p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
root=a.directory.resolve();report=[];bridge=CvBridge()
def rotation(rpy):
    r,p,y=rpy;cr,sr=math.cos(r),math.sin(r);cp,sp=math.cos(p),math.sin(p);cy,sy=math.cos(y),math.sin(y)
    rx=np.array([[1,0,0],[0,cr,-sr],[0,sr,cr]]);ry=np.array([[cp,0,sp],[0,1,0],[-sp,0,cp]]);rz=np.array([[cy,-sy,0],[sy,cy,0],[0,0,1]])
    return rz@ry@rx
for variant in ['default','nondefault']:
    directory=root/variant;calibration=yaml.safe_load((directory/'extrinsics.yaml').read_text())
    records=[json.loads(line) for line in (directory/'clock_observations.jsonl').read_text().splitlines()]
    assert len(records)>=3
    scan_wanted={round(row['scan_s']*1e9) for row in records[:3]};image_wanted={round(row['image_s']*1e9) for row in records[:3]}
    scans={};images={};reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(directory/'bag'),storage_id='sqlite3'),rosbag2_py.ConverterOptions('',''))
    while reader.has_next() and (len(scans)<len(scan_wanted) or len(images)<len(image_wanted)):
        topic,payload,_=reader.read_next()
        if topic not in ['/scan','/camera/image_raw']:continue
        message=deserialize_message(payload,LaserScan if topic=='/scan' else Image)
        stamp=message.header.stamp.sec*10**9+message.header.stamp.nanosec
        if topic=='/scan' and stamp in scan_wanted:scans[stamp]=message
        if topic=='/camera/image_raw' and stamp in image_wanted:images[stamp]=message
    laser,camera=calibration['laser_link'],calibration['camera_link'];assert laser['parent']==camera['parent']=='base_link'
    rl,rc=rotation(laser.get('rpy',[0,0,0])),rotation(camera.get('rpy',[0,0,0]))
    tl,tc=np.asarray(laser['xyz']),np.asarray(camera['xyz']);k=calibration['camera_intrinsics']
    for index,row in enumerate(records[:3],1):
        scan=scans[round(row['scan_s']*1e9)];message=images[round(row['image_s']*1e9)]
        expected=bridge.imgmsg_to_cv2(message,'rgb8').copy();colored=0;expected_points=[]
        for beam,distance in enumerate(scan.ranges):
            if not math.isfinite(distance) or not scan.range_min<=distance<=scan.range_max:continue
            angle=scan.angle_min+beam*scan.angle_increment
            local=np.array([distance*math.cos(angle),distance*math.sin(angle),0])
            point=rc.T@(rl@local+tl-tc)
            if point[0]<=1e-5:continue
            u=int(np.rint(k['cx']-k['fx']*point[1]/point[0]));v=int(np.rint(k['cy']-k['fy']*point[2]/point[0]))
            if not(0<=u<message.width and 0<=v<message.height):continue
            weight=min(1.,max(0.,(distance-scan.range_min)/(scan.range_max-scan.range_min)))
            cv2.circle(expected,(u,v),3,(int(255*(1-weight)),0,int(255*weight)),-1);colored+=1
            expected_points.append(dict(beam_index=beam,distance_m=distance,pixel=[u,v],camera_body_xyz_m=point.tolist()))
        actual=cv2.cvtColor(cv2.imread(str(directory/f'projection_{index:03d}.png')),cv2.COLOR_BGR2RGB)
        assert colored==row['visible_points'] and np.array_equal(actual,expected),(variant,index,np.count_nonzero(actual!=expected))
        assert abs(row['scan_s']-row['image_s'])<=.05+1e-9
        correspondences=json.loads((directory/f'projection_{index:03d}.points.json').read_text())
        assert correspondences['scan_stamp_ns']==scan.header.stamp.sec*10**9+scan.header.stamp.nanosec
        assert correspondences['image_stamp_ns']==message.header.stamp.sec*10**9+message.header.stamp.nanosec
        assert len(correspondences['points'])==len(expected_points)
        for actual_point,expected_point in zip(correspondences['points'],expected_points):
            assert actual_point['beam_index']==expected_point['beam_index']
            assert actual_point['pixel']==expected_point['pixel']
            assert actual_point['distance_m']==expected_point['distance_m']
            assert np.allclose(actual_point['camera_body_xyz_m'],expected_point['camera_body_xyz_m'],atol=1e-10,rtol=0)
        report.append(dict(variant=variant,image=index,visible_points=colored,pixel_exact=True,
                           point_distance_correspondences_verified=len(expected_points),
                           sha256=hashlib.sha256(actual.tobytes()).hexdigest()))
    viewer=json.loads((directory/'clock_switch_demo.json').read_text());assert viewer['received_debug_images']>=10
    assert viewer['encodings']==['rgb8'] and viewer['image_shapes']==[[640,480]]
    assert viewer['observed_clock_modes']==([False,True] if variant=='nondefault' else [True])
    if variant=='nondefault':
        assert k['fx']==420 and k['fy']==440 and laser['xyz'][2]==.45 and camera['xyz'][2]==.75
        assert records[0]['median_projected_v']>k['cy']
graphs=list(root.glob('*.gv'));assert graphs
assert any(all(name in path.read_text() for name in ['map','odom','base_link','laser_link','camera_link']) for path in graphs)
(root/'pixel_oracle.json').write_text(json.dumps(dict(status='PASS',images=report,actual_tf_graph_checked=True,nondefault_viewer=viewer),indent=2))
print('PROJECTION_ORACLE_PASS',len(report),'actual saved images, nativeTF and live RGB topic')
