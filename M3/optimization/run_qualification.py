"""A fixed, sequential qualification schedule; every attempt is retained."""
import argparse
import json
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(); p.add_argument('--suite',choices=['main','extended'],default='main'); p.add_argument('--prefix',default=''); a=p.parse_args()
schedule=[]
if a.suite=='main':
    for label,runs in [('B',3),('A',3),('B_tuned',10)]:
        schedule.append(dict(label='formal_static_'+label,runs=runs,profile=label,seed=200))
    for label in ['A','B','B_tuned']:
        schedule.append(dict(label='formal_dynamic_'+label,runs=10,profile=label,seed=200,obstacle='8.0,1.6'))
    schedule.append(dict(label='tuning_speed_only',runs=3,profile='B_speed',seed=200,obstacle='8.0,1.6'))
else:
    schedule=[dict(label='heldout_obstacle_east',runs=2,profile='B_tuned',seed=400,obstacle='9.5,1.4'),
              dict(label='heldout_obstacle_gate_exit',runs=2,profile='B_tuned',seed=402,obstacle='7.0,1.3'),
              dict(label='heldout_goal_northeast',runs=2,profile='B_tuned',seed=404,goal='9,6,3.141592653589793'),
              dict(label='heldout_goal_far_northwest',runs=2,profile='B_tuned',seed=406,goal='0,6,-1.5707963267948966'),
              dict(label='boundary_blocked_goal',runs=1,profile='B_tuned',seed=408,obstacle='11,5',size=.8,timeout=90),
              dict(label='boundary_close_front',runs=1,profile='B_tuned',seed=410,obstacle='2.8,1.0',size=.6,timeout=90)]
out=ROOT/'M3/optimization/results'/(time.strftime('%Y%m%d_%H%M%S')+'_qualification_'+a.suite); out.mkdir(parents=True)
(out/'schedule.json').write_text(json.dumps(schedule,indent=2))
manifest=[]
for item in schedule:
    before=set((ROOT/'M3/optimization/results').iterdir())
    command=[str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M3/optimization/run_navigation_trial.py'),
             '--label',a.prefix+item['label'],'--runs',str(item['runs']),'--seed',str(item['seed']),
             '--params',str(ROOT/'M3/M3-4/config'/('planner_'+item['profile']+'_params.yaml')),
             '--timeout',str(item.get('timeout',150))]
    if item.get('obstacle'): command+=['--obstacle-at',item['obstacle'],'--obstacle-size',str(item.get('size',.6)),'--viewer']
    if item.get('goal'): command+=['--goal',item['goal']]
    with (out/(item['label']+'.log')).open('w') as log:
        result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    created=set((ROOT/'M3/optimization/results').iterdir())-before
    manifest.append(dict(**item,returncode=result.returncode,result_dirs=[str(path.relative_to(ROOT)) for path in sorted(created)]))
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('QUALIFICATION_GROUP '+json.dumps(manifest[-1]),flush=True)
    if result.returncode: raise RuntimeError('Infrastructure error; no automatic replacement of failed attempts: '+str(out))
print('QUALIFICATION_FINISHED',out,flush=True)
