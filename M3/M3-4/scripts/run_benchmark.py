import argparse
import json
import subprocess
import time
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[3]


def main():
    p=argparse.ArgumentParser(); p.add_argument('--planners',default='A,B,B_tuned'); p.add_argument('--runs',type=int,default=10); p.add_argument('--obstacle-at',default='8.0,1.6'); p.add_argument('--delay',default='3.0'); p.add_argument('--obstacle-size',default='.6')
    p.add_argument('--resume-manifest'); a=p.parse_args()
    folder=ROOT/'M3/M3-4/config'; folder.mkdir(parents=True,exist_ok=True)
    base=yaml.safe_load((ROOT/'M3/M3-3/config/nav2_params.yaml').read_text()); generated={}
    for label,speed,lookahead,collision in [('A',.28,.7,2.),('B',.65,.25,.5),('B_tuned',.45,.5,1.5)]:
        data=yaml.safe_load(yaml.safe_dump(base)); follow=data['controller_server']['ros__parameters']['FollowPath']; follow.update(desired_linear_vel=speed,lookahead_dist=lookahead,min_lookahead_dist=lookahead,max_lookahead_dist=lookahead,use_velocity_scaled_lookahead_dist=False,max_allowed_time_to_collision_up_to_carrot=collision)
        data['velocity_smoother']['ros__parameters']['max_velocity']=[.75,0.,1.2]
        path=folder/('planner_'+label+'_params.yaml'); path.write_text('# Same actual car/map/goal; bounded forward-only RPP.\n'+yaml.safe_dump(data)); generated[label]=path
    manifest=json.loads(Path(a.resume_manifest).read_text()) if a.resume_manifest else []; output=ROOT/'M3/M3-4/results'/time.strftime('%Y%m%d_%H%M%S'); output.mkdir(parents=True)
    for label in a.planners.split(','):
      for attempt in range(4):
        qualified=0
        for item in manifest:
            if item['planner']!=label: continue
            for directory in item['result_dirs']:
                for file in (ROOT/directory).glob('run_*/result.json'):
                    r=json.loads(file.read_text()); obstacle=r.get('obstacle') or {}
                    if obstacle.get('success') and obstacle.get('world_xy')==a.obstacle_at: qualified+=1
        if qualified>=a.runs: break
        before=set((ROOT/'M3/M3-3/results').iterdir()); log=(output/(label+'_'+str(attempt)+'.log')).open('w')
        result=subprocess.run([str(ROOT/'.venv-ros/bin/python'),str(ROOT/'scripts/verify_navigation.py'),'--runs',str(a.runs-qualified),'--params',str(generated[label]),'--label','dynamic_'+label,'--domain-base',str(100+attempt*20),'--obstacle-at',a.obstacle_at,'--delay',a.delay,'--obstacle-size',a.obstacle_size],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        log.close(); new=set((ROOT/'M3/M3-3/results').iterdir())-before
        manifest.append(dict(planner=label,returncode=result.returncode,result_dirs=[str(p.relative_to(ROOT)) for p in new])); (output/'manifest.json').write_text(json.dumps(manifest,indent=2))
        if result.returncode==0: break
      else: raise RuntimeError('Repeated infrastructure failure; original logs retained: '+label)
    print(str(output),flush=True)


if __name__=='__main__': main()
