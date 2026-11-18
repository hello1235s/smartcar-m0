import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True); p.add_argument('--baseline',required=True); p.add_argument('--out',required=True); a=p.parse_args(); root=Path(__file__).resolve().parents[3]; out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    baseline=json.loads(Path(a.baseline).read_text()); baselines=baseline if isinstance(baseline,dict) else {k:baseline for k in ['A','B','B_tuned']}; rows=[]; trajectories=[]
    baseline_plan_lengths={}
    for label in baselines:
        lengths=[]
        for directory in (root/'M3/M3-3/results').glob('*_matched_baseline_'+label):
            for file in directory.glob('run_*/plans.json'):
                plans=json.loads(file.read_text())
                if plans: lengths.append(sum(math.dist(a,b) for a,b in zip(plans[0]['points'],plans[0]['points'][1:])))
        baseline_plan_lengths[label]=float(np.mean(lengths)) if lengths else None
    for experiment in json.loads(Path(a.manifest).read_text()):
        for directory in experiment['result_dirs']:
            for run in sorted((root/directory).glob('run_*')):
                if not (run/'result.json').exists(): continue
                r=json.loads((run/'result.json').read_text()); references=[b['path_length_m'] for b in baselines[experiment['planner']] if b['success']]; length=float(np.mean(references)) if references else None
                plans=json.loads((run/'plans.json').read_text()); injected=(r.get('obstacle') or {}).get('sim_t'); chosen=next((i for i,p in enumerate(plans) if injected is not None and p['t']>=injected+3 and p['points']),None); planned_extra=None
                reference=baseline_plan_lengths[experiment['planner']]
                if chosen is not None and reference is not None:
                    prefix=[p['points'][0] for p in plans[:chosen+1] if p['points']]; remaining=plans[chosen]['points']
                    planned_extra=sum(math.dist(a,b) for a,b in zip(prefix,prefix[1:]))+sum(math.dist(a,b) for a,b in zip(remaining,remaining[1:]))-reference
                rows.append(dict(planner=experiment['planner'],run=run.name,success=r['success'],seconds=r['sim_seconds'],length_m=r['path_length_m'],extra_length_m=planned_extra,odom_extra_length_m=r['path_length_m']-length if length is not None else None,steering_variation_rad_per_m=r['steering_variation_rad_per_m'],first_replan_after_injection_s=r['first_plan_after_injection_delay_s']))
                trajectories.append((experiment['planner'],list(csv.DictReader((run/'trajectory.csv').open()))))
    with (out/'benchmark.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    labels=list(dict.fromkeys(r['planner'] for r in rows)); summary=[]
    for label in labels:
        group=[r for r in rows if r['planner']==label]; successful=[r for r in group if r['success']]
        summary.append(dict(planner=label,attempts=len(group),successes=len(successful),success_rate=len(successful)/len(group),**{k:float(np.mean([r[k] for r in successful if r[k] is not None])) if any(r[k] is not None for r in successful) else None for k in ['seconds','extra_length_m','steering_variation_rad_per_m']}))
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    (out/'distance_method.json').write_text(json.dumps(dict(primary='global-plan estimate: traveled plan-start prefix plus remaining plan at least 3s after insertion, minus matched initial no-obstacle plan length',reference_plan_lengths_m=baseline_plan_lengths,secondary='odom integral minus mean successful no-obstacle odom integral; undefined when that controller has no successful reference'),indent=2))
    fig,axes=plt.subplots(2,2,figsize=(10,7))
    for ax,key in zip(axes.flat,['success_rate','seconds','extra_length_m','steering_variation_rad_per_m']):
        ax.bar(labels,[s[key] if s[key] is not None else np.nan for s in summary]); ax.set_title(key)
    fig.tight_layout(); fig.savefig(out/'metrics.png',dpi=160); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,6)); colors=dict(zip(labels,['#177e89','#db5c46','#7a62ad']))
    for label,trajectory in trajectories: ax.plot([float(r['x']) for r in trajectory],[float(r['y']) for r in trajectory],alpha=.3,c=colors[label])
    for label in labels: ax.plot([],[],c=colors[label],label=label)
    ax.legend(); ax.set_aspect('equal'); ax.set(xlabel='odom x (m)',ylabel='odom y (m)',title='Actual recorded trajectories; odometry, not corrected ground truth'); fig.tight_layout(); fig.savefig(out/'trajectories.png',dpi=160); plt.close(fig); print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
