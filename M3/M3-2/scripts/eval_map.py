import argparse
import json
from pathlib import Path
import cv2
import numpy as np
import yaml
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser(); p.add_argument('--map',required=True); p.add_argument('--out',required=True); a=p.parse_args()
    path=Path(a.map); info=yaml.safe_load(path.read_text()); image=cv2.imread(str(path.parent/info['image']),0); resolution=info['resolution']; ox,oy,_=info['origin']; out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    y,x=np.where(image<80); wx=ox+(x+.5)*resolution; wy=oy+(image.shape[0]-y-.5)*resolution
    # Survey region selection only; fitting uses occupied pixels from actual SLAM.
    mask=(wx>.5)&(wx<10)&(wy>6.7)&(wy<7.4); wall=np.column_stack((wx[mask],wy[mask])); fit=np.polyfit(wall[:,0],wall[:,1],1); residual=np.abs(wall[:,1]-np.polyval(fit,wall[:,0]))/np.sqrt(1+fit[0]**2)
    # Each column's black-pixel cluster count: distinguish wall thickness from a second separated line.
    clusters=[]; thickness=[]
    for column in range(image.shape[1]):
        xx=ox+(column+.5)*resolution
        if not .5<xx<10: continue
        indices=y[(x==column)&mask]
        if len(indices):
            indices=np.sort(indices); groups=1+np.count_nonzero(np.diff(indices)>2); clusters.append(int(groups)); thickness.append((indices.max()-indices.min()+1)*resolution)
    # At gate x_world=6 => map x=5, inner corners map y=-.5,+.5.
    gate=[]
    for row in range(image.shape[0]):
        yy=oy+(image.shape[0]-row-.5)*resolution
        if -.5<yy<.5:
            column=int((5-ox)/resolution)
            gate.append(int(image[row,column])>240)
    report=dict(resolution_m=resolution,wall_points=len(wall),wall_fit_slope=float(fit[0]),wall_rms_m=float(np.sqrt(np.mean(residual**2))),wall_max_deviation_m=float(residual.max()),loop_wall_columns=len(clusters),loop_wall_double_clusters=sum(c>1 for c in clusters),loop_wall_observed_thickness_max_m=max(thickness),ghost_separation_detection_limit_m=2*resolution,gate_free_cells=sum(gate),gate_measured_free_width_m=sum(gate)*resolution,unknown_fraction=float(np.mean((image>80)&(image<240))),method='Quantities from actual occupancy image. Zero double clusters does not prove sub-grid zero drift.')
    (out/'quality.json').write_text(json.dumps(report,indent=2)); fig,ax=plt.subplots(figsize=(10,6)); ax.imshow(image,cmap='gray',origin='upper',extent=[ox,ox+image.shape[1]*resolution,oy,oy+image.shape[0]*resolution]); ax.scatter(wall[:,0],wall[:,1],s=4,c='#d44939',label='SLAM occupied wall points'); ax.set(xlabel='map x (m)',ylabel='map y (m)',title='Actual slam_toolbox occupancy map'); ax.legend(); ax.set_aspect('equal'); fig.tight_layout(); fig.savefig(out/'map_quality.png',dpi=170); plt.close(fig); print(json.dumps(report,indent=2))


if __name__=='__main__': main()
