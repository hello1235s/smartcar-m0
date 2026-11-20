"""Recompute strict results and all four metrics from every retained attempt."""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import statistics
import sys
import yaml
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'M3/common'))
from evaluation import scene_obstacles,rectangle


def average(values):
    clean=[v for v in values if v is not None and math.isfinite(v)]
    return statistics.mean(clean) if clean else None


def interval(k,n):
    z=1.96; center=(k/n+z*z/(2*n))/(1+z*z/n)
    half=z*math.sqrt(k/n*(1-k/n)/n+z*z/(4*n*n))/(1+z*z/n)
    return [center-half,center+half]


def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--out',type=Path,default=ROOT/'M3/optimization/report'); a=p.parse_args()
    a.manifest=a.manifest.resolve()
    out=a.out; out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads(a.manifest.read_text()); rows=[]; raw=[]
    experiment_metadata=[]; profile_configs={}
    for group in manifest:
        for directory in group['result_dirs']:
            folder=ROOT/directory; metadata=json.loads((folder/'experiment.json').read_text())
            experiment_metadata.append((group,metadata))
            config=yaml.safe_load((folder/'parameters_used.yaml').read_text())
            for key in ['default_nav_to_pose_bt_xml','default_nav_through_poses_bt_xml']:
                config['bt_navigator']['ros__parameters'][key]=Path(config['bt_navigator']['ros__parameters'][key]).name
            label=group['profile']
            if label in profile_configs and config!=profile_configs[label]:
                raise RuntimeError('Mismatched control settings in same-profile reference/comparison: '+label)
            profile_configs[label]=config
            files=sorted(folder.glob('run_*/result.json'))
            if len(files)!=group['runs']: raise RuntimeError('Missing attempts; refuse partial headline: '+directory)
            for file in files:
                r=json.loads(file.read_text()); actual=list(csv.DictReader((file.parent/'world_truth.csv').open()))
                truth_length=sum(math.hypot(float(y['world_x'])-float(x['world_x']),float(y['world_y'])-float(x['world_y'])) for x,y in zip(actual,actual[1:]))
                if abs(truth_length-r['path_length_m'])>1e-8: raise RuntimeError('Truth path integral does not match result: '+str(file))
                error=r.get('endpoint_error_world_truth') or {}
                row=dict(group=group['label'],profile=group['profile'],run=file.parent.name,seed=metadata['base_seed']+int(file.parent.name[-2:])-1,
                         result_dir=str(file.parent.relative_to(ROOT)),success=r['success'],action_success=r['action_success'],accepted=r['goal_accepted'],
                         seconds=r['sim_seconds'],truth_length_m=truth_length,odom_length_m=r['odom_path_length_m'],
                         position_error_m=error.get('position_m'),yaw_error_rad=error.get('yaw_rad'),
                         minimum_clearance_m=r['minimum_geometric_clearance_m'],overlap_samples=r['geometric_overlap_samples'],
                         steering_variation_rad_per_m=r['steering_variation_rad_per_m'],
                         first_plan_after_injection_s=r['first_plan_after_injection_delay_s'],
                         final_linear_speed_mps=(r.get('final_measured_speed') or [None])[0],
                         controller_command_samples=r.get('controller_command_samples',0),
                         controller_curvature_violation_samples=r.get('controller_curvature_violation_samples'),
                         maximum_requested_curvature_1_per_m=r.get('maximum_requested_curvature_1_per_m'),
                         obstacle_distance_to_initial_path_m=r.get('obstacle_distance_to_initial_path_m'),
                         failure=';'.join(r['qualification_failures']),map_sha256=metadata['map_sha256'],map_yaml_sha256=metadata.get('map_yaml_sha256'),params_sha256=metadata['params_sha256'],extra_length_m=None)
                rows.append(row); raw.append((row,r))
    for key in ['map_sha256','map_yaml_sha256','goal_checker_library_sha256','ackermann_controller_library_sha256','rmw_implementation','tf2_core_library_sha256']:
        if len({m.get(key) for _,m in experiment_metadata})>1:
            raise RuntimeError('Mixed map, runtime or control kernel cannot share one comparison: '+key)
    formal=[m for g,m in experiment_metadata if g['label'].startswith('formal_dynamic_')]
    for key in ['goal_map','obstacle_at','obstacle_size','delay_s']:
        if len({str(m.get(key)) for m in formal})>1: raise RuntimeError('Different formal dynamic conditions: '+key)
    references={label:[r['truth_length_m'] for r in rows if r['group']=='formal_static_'+label and r['success']] for label in ['A','B','B_tuned']}
    summaries=[]
    for group in manifest:
        records=[r for r in rows if r['group']==group['label']]; successes=[r for r in records if r['success']]
        ref=average(references.get(group['profile'],[]))
        for row in records:
            if group.get('obstacle') and row['success'] and ref is not None: row['extra_length_m']=row['truth_length_m']-ref
        failure_counts=Counter(reason for row in records for reason in row['failure'].split(';') if reason)
        summaries.append(dict(group=group['label'],profile=group['profile'],attempts=len(records),accepted=sum(r['accepted'] for r in records),
                              successes=len(successes),success_rate=len(successes)/len(records),wilson_95=interval(len(successes),len(records)),
                              mean_seconds=average([r['seconds'] for r in successes]),mean_extra_length_m=average([r['extra_length_m'] for r in successes]),
                              mean_steering_variation_rad_per_m=average([r['steering_variation_rad_per_m'] for r in successes]),
                              mean_position_error_m=average([r['position_error_m'] for r in successes]),max_position_error_m=max([r['position_error_m'] for r in successes],default=None),
                              max_yaw_error_rad=max([r['yaw_error_rad'] for r in successes],default=None),
                              minimum_clearance_all_attempts_m=min([r['minimum_clearance_m'] for r in records if r['minimum_clearance_m'] is not None],default=None),
                              controller_curvature_violation_samples=sum(r['controller_curvature_violation_samples'] or 0 for r in records),
                              controller_command_samples=sum(r['controller_command_samples'] for r in records),
                              no_obstacle_reference_successes=len(references.get(group['profile'],[])),no_obstacle_reference_mean_m=ref,
                              failure_reasons=dict(failure_counts)))
    with (out/'all_attempts.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (out/'summary.json').write_text(json.dumps(summaries,indent=2))
    (out/'method.json').write_text(json.dumps(dict(manifest=str(a.manifest.relative_to(ROOT)),
        success='Action success AND truth endpoint <=0.15m/0.20rad AND >=5m AND no conservative-envelope overlap AND sufficient scan/truth samples AND requested obstacle inserted',
        distance='world truth integral minus mean successful no-obstacle integral for the same profile; unavailable if no successful reference',
        time='simulated action duration; excludes post-action settling',smoothness='TV of bridge commanded steering atan(0.28*omega/v) when abs(v)>.005m/s, otherwise0, divided by truth distance; command proxy, not steering-joint measurement',
        safety='Known world-box geometry against conservative body/wheel envelope sampled from ModelStates; not contact-sensor certification',
        randomization='Gazebo seeds recorded; AMCL scheduling and random sampling are not bitwise deterministic',
        means='Time, detour, smoothness and endpoint means use qualified successes only. All failures remain in denominator and CSV. Negative distance differences are retained, including run-to-run path/localization variation.'),indent=2))
    dynamic=[s for s in summaries if s['group'].startswith('formal_dynamic_')]
    if dynamic:
        fig,axes=plt.subplots(2,2,figsize=(10,7)); labels=[s['profile'] for s in dynamic]
        for ax,key,title in zip(axes.flat,['success_rate','mean_seconds','mean_extra_length_m','mean_steering_variation_rad_per_m'],['Strict success rate','Mean successful time (sim s)','Actual extra distance (m)','Command steering TV (rad/m)']):
            values=[s[key] for s in dynamic]; ax.bar(labels,[v if v is not None else 0 for v in values],color=['#237b86','#d65c47','#6b61a8'])
            for i,value in enumerate(values):
                if value is None: ax.text(i,0,'N/A',ha='center',va='bottom')
                elif key=='success_rate':
                    lower,upper=dynamic[i]['wilson_95']
                    ax.errorbar(i,value,yerr=[[max(0.,value-lower)],[max(0.,upper-value)]],fmt='none',color='#243b47',capsize=5)
                    ax.text(i,min(1.08,max(value,upper)+.035),f"{dynamic[i]['successes']}/{dynamic[i]['attempts']}",ha='center',fontsize=10)
                else: ax.annotate(f'{value:.2f}',(i,value),xytext=(0,3 if value>=0 else -3),textcoords='offset points',ha='center',va='bottom' if value>=0 else 'top',fontsize=10)
            ax.set_title(title); ax.grid(axis='y',alpha=.2)
            if key!='success_rate': ax.margins(y=.17)
        axes[0,0].set_ylim(0,1.15); fig.tight_layout(); fig.savefig(out/'metrics.png',dpi=170); plt.close(fig)
        fig,ax=plt.subplots(figsize=(10,7)); colors={'A':'#237b86','B':'#d65c47','B_tuned':'#6b61a8'}
        for _,shape in scene_obstacles(): ax.add_patch(Polygon(shape,facecolor='#cbd4d7',edgecolor='#546b75'))
        obstacles={(m['obstacle_at'],m['obstacle_size'],m['delay_s']) for m in formal if m.get('obstacle_at')}
        for location,size,delay in sorted(obstacles):
            x,y=map(float,location.split(','))
            ax.add_patch(Polygon(rectangle(x,y,size,size),facecolor='#f6bd60',edgecolor='#9d5b00',label=f'Inserted obstacle after {delay:g}s'))
        for row in rows:
            if not row['group'].startswith('formal_dynamic_'): continue
            points=list(csv.DictReader((ROOT/row['result_dir']/'world_truth.csv').open()))
            ax.plot([float(p['world_x']) for p in points],[float(p['world_y']) for p in points],color=colors[row['profile']],alpha=.3)
        for label in labels: ax.plot([],[],color=colors[label],label=label)
        ax.set(xlim=(-.4,12.4),ylim=(-.4,8.4),xlabel='world x (m)',ylabel='world y (m)',title='All retained actual world trajectories, including failures'); ax.set_aspect('equal'); ax.legend(); fig.tight_layout(); fig.savefig(out/'trajectories.png',dpi=170); plt.close(fig)
    # Replanning after actual FollowPath failures is separate from periodic replanning after injection.
    replans=[dict(result_dir=row['result_dir'],**event) for row,r in raw for event in r.get('controller_failure_replans',[])]
    (out/'failure_replans.json').write_text(json.dumps(replans,indent=2))
    # Representative real costmap messages and velocity commands; retain original arrays alongside figures.
    successful=next((row for row in rows if row['group']=='formal_static_B_tuned' and row['success']),None)
    if successful:
        directory=ROOT/successful['result_dir']; maps=json.loads((directory/'costmaps.json').read_text())
        fig,axes=plt.subplots(1,2,figsize=(11,5))
        for ax,label in zip(axes,['global','local']):
            m=maps[label]; array=np.array(m['data']).reshape(m['height'],m['width']); x,y=m['origin']; res=m['resolution']
            ax.imshow(array,origin='lower',extent=[x,x+res*m['width'],y,y+res*m['height']],vmin=-1,vmax=100,cmap='magma')
            ax.set_title(label+' costmap: actual ROS message'); ax.set_aspect('equal')
        fig.tight_layout(); fig.savefig(out/'costmaps.png',dpi=170); plt.close(fig)
        commands=list(csv.DictReader((directory/'commands.csv').open())); t=np.array([float(r['t']) for r in commands]); t-=t[0]
        fig,axes=plt.subplots(2,1,figsize=(10,5),sharex=True)
        axes[0].plot(t,[float(r['v']) for r in commands]); axes[0].set_ylabel('v (m/s)')
        axes[1].plot(t,[float(r['omega']) for r in commands]); axes[1].set(xlabel='sim time since first command (s)',ylabel='omega (rad/s)')
        fig.tight_layout(); fig.savefig(out/'commands.png',dpi=170); plt.close(fig)
    print(json.dumps(summaries,indent=2))


if __name__=='__main__': main()
