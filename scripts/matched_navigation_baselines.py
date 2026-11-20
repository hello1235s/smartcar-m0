"""Collect independent no-obstacle references without overwriting history."""
import argparse
import json
from pathlib import Path
import subprocess
import time
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(); p.add_argument('--runs',type=int,default=3); p.add_argument('--seed',type=int,default=200); p.add_argument('--planners',default='A,B,B_tuned'); a=p.parse_args()
out=ROOT/'M3/optimization/results'/(time.strftime('%Y%m%d_%H%M%S')+'_matched_baselines'); out.mkdir(parents=True)
manifest=[]
for label in a.planners.split(','):
    if label not in ['A','B','B_tuned','B_speed']: raise ValueError('Unknown profile '+label)
    before=set((ROOT/'M3/optimization/results').iterdir())
    with (out/(label+'.log')).open('w') as log:
        result=subprocess.run([str(ROOT/'.venv-ros/bin/python'),str(ROOT/'M3/optimization/run_navigation_trial.py'),
            '--runs',str(a.runs),'--label','formal_static_'+label,'--seed',str(a.seed),
            '--params',str(ROOT/'M3/M3-4/config'/('planner_'+label+'_params.yaml'))],stdout=log,stderr=subprocess.STDOUT)
    created=set((ROOT/'M3/optimization/results').iterdir())-before
    manifest.append(dict(label='formal_static_'+label,runs=a.runs,profile=label,returncode=result.returncode,result_dirs=[str(path.relative_to(ROOT)) for path in sorted(created)]))
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    if result.returncode: raise RuntimeError('Infrastructure failure retained: '+str(out))
print('BASELINES_FINISHED',out)
