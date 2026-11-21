"""Additional raw-pose audit for the camera's 1cm front protrusion.

Original body/wheel scores remain unchanged. This is a separate, stricter
front-bound check, not a contact-sensor or continuous-time collision test.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'M3/common'))
from evaluation import clearance,rectangle,scene_obstacles
p=argparse.ArgumentParser(); p.add_argument('--main',type=Path,required=True); p.add_argument('--extended',type=Path,required=True); a=p.parse_args()
rows=[]
for manifest in [a.main,a.extended]:
    for group in json.loads(manifest.read_text()):
        for directory in group['result_dirs']:
            folder=ROOT/directory; model=ET.parse(folder/'model_used.urdf').getroot()
            body_offset=float(model.find("joint[@name='base_footprint_joint']/origin").get('xyz').split()[0])
            camera=model.find("joint[@name='camera_joint']/origin")
            assert all(abs(float(x))<1e-9 for x in camera.get('rpy').split())
            camera_offset=float(camera.get('xyz').split()[0])
            camera_length=float(model.find("link[@name='camera_link']/collision/geometry/box").get('size').split()[0])
            body_length=float(model.find("link[@name='base_link']/collision/geometry/box").get('size').split()[0])
            rear=body_offset-body_length/2
            front=max(body_offset+body_length/2,body_offset+camera_offset+camera_length/2)
            assert abs(rear+.085)<1e-8 and abs(front-.375)<1e-8
            for path in sorted(folder.glob('run_*/result.json')):
                result=json.loads(path.read_text()); obstacle=result['obstacle']; minimum=float('inf'); overlaps=0; samples=0
                for pose in csv.DictReader((path.parent/'world_truth.csv').open()):
                    x,y,yaw=map(float,[pose['world_x'],pose['world_y'],pose['yaw']]); c,s=math.cos(yaw),math.sin(yaw)
                    polygon=[(x+c*px-s*py,y+s*px+c*py) for px,py in [(rear,-.13),(front,-.13),(front,.13),(rear,.13)]]
                    active=scene_obstacles()
                    if obstacle and obstacle['success'] and float(pose['t'])>=obstacle['confirmed_sim_t']:
                        ox,oy=map(float,obstacle['world_xy'].split(',')); active.append(('temporary_obstacle',rectangle(ox,oy,obstacle['size'],obstacle['size'])))
                    gap=min(clearance(polygon,shape) for _,shape in active)
                    minimum=min(minimum,gap); overlaps+=gap<0; samples+=1
                rows.append(dict(source=str(path.parent.relative_to(ROOT)),samples=samples,minimum_clearance_m=minimum,overlap_samples=overlaps))
report=dict(status='PASS' if rows and all(row['overlap_samples']==0 for row in rows) else 'REVIEW',
    rear_frame_bounds_m=dict(x_min=-.085,x_max=.375,y_min=-.13,y_max=.13),
    additional_front_margin_m=.01, runs=len(rows),minimum_clearance_m=min(row['minimum_clearance_m'] for row in rows),
    note='Camera front extent derived from each archived actual URDF: .14+.22+.03/2=.375m, 1cm beyond the body. Extra front-bound audit only; original body/wheel scores and denominators are not rewritten. Known-box geometry at recorded pose samples, not continuous contact certification.',cases=rows)
out=ROOT/'M3/optimization/report/camera_margin_audit.json'; out.write_text(json.dumps(report,indent=2))
print('CAMERA_FRONT_MARGIN_AUDIT',report['status'],len(rows),report['minimum_clearance_m'],flush=True)
assert report['status']=='PASS',report
