"""Run every requested profile under identical, independently checked conditions."""
import argparse
import json
from pathlib import Path
import subprocess
import time
ROOT=Path(__file__).resolve().parents[3]


def main():
    p=argparse.ArgumentParser(); p.add_argument('--planners',default='A,B,B_tuned'); p.add_argument('--runs',type=int,default=10)
    p.add_argument('--obstacle-at',default='8.0,1.6'); p.add_argument('--delay',default='3.0'); p.add_argument('--obstacle-size',default='.6')
    p.add_argument('--seed',type=int,default=200); p.add_argument('--baseline-runs',type=int,default=3); p.add_argument('--out',type=Path)
    p.add_argument('--nominal-static-runs',type=int,default=10)
    p.add_argument('--injection-reference',choices=['accepted','motion'],default='motion')
    a=p.parse_args(); labels=a.planners.split(',')
    if any(label not in ['A','B','B_tuned'] for label in labels): p.error('Unknown planner profile')
    output=a.out or ROOT/'M3/M3-4/results'/time.strftime('%Y%m%d_%H%M%S'); output.mkdir(parents=True,exist_ok=False)
    python=str(ROOT/'.venv-ros/bin/python')
    subprocess.run([python,str(ROOT/'M3/M3-4/scripts/make_profiles.py')],check=True)
    manifest=[]
    for mode in ['static','dynamic']:
        for label in labels:
            before=set((ROOT/'M3/optimization/results').iterdir())
            name='formal_'+mode+'_'+label
            runs=(a.nominal_static_runs if label=='B_tuned' else a.baseline_runs) if mode=='static' else a.runs
            command=[python,str(ROOT/'M3/optimization/run_navigation_trial.py'),'--runs',str(runs),'--label',name,'--seed',str(a.seed),
                     '--params',str(ROOT/'M3/M3-4/config'/('planner_'+label+'_params.yaml')),
                     '--injection-reference',a.injection_reference,'--viewer']
            if mode=='dynamic': command+=['--obstacle-at',a.obstacle_at,'--delay',a.delay,'--obstacle-size',a.obstacle_size]
            with (output/(name+'.log')).open('w') as log: result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            after=set((ROOT/'M3/optimization/results').iterdir())-before
            manifest.append(dict(label=name,runs=runs,profile=label,seed=a.seed,obstacle=a.obstacle_at if mode=='dynamic' else None,
                                 returncode=result.returncode,result_dirs=[str(path.relative_to(ROOT)) for path in sorted(after)]))
            (output/'manifest.json').write_text(json.dumps(manifest,indent=2))
            if result.returncode: raise RuntimeError('Infrastructure failure retained: '+str(output))
    subprocess.run([python,str(ROOT/'M3/optimization/analyze_qualification.py'),'--manifest',str(output/'manifest.json'),'--out',str(output/'analysis')],check=True)
    print('BENCHMARK_FINISHED',output)


if __name__=='__main__': main()
