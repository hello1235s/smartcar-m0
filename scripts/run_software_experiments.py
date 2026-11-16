import json
import subprocess
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; python=str(ROOT/'.venv-ros/bin/python'); tool=str(ROOT/'M5/M5-4/exp.py')
def run(args): subprocess.run([python,tool]+args,cwd=ROOT,check=True)
stamp=time.strftime('%H%M%S'); names=['software_base_'+stamp,'software_low_conf_'+stamp]
for name,conf,count in [(names[0],'.25',3),(names[1],'.65',2)]:
    run(['new','--name',name,'--base',str(ROOT/'M5/M5-4/scene_training.yaml'),'--set','confidence='+conf,'--desc','Actual ROS/MCAP software contract runs; no physical navigation/grasp claim'])
    model=ROOT/('M6/M6-1/models/best_fp32.onnx' if count==3 else 'M6/M6-2/models/static_qdq.onnx')
    run(['run','--name',name,'--runs',str(count),'--model',str(model)])
run(['compare','--names',','.join(names)])
(ROOT/'M5/experiments/latest.json').write_text(json.dumps(dict(experiments=names,runs=5),indent=2)); print('FIVE_ACTUAL_SOFTWARE_RUNS_COMPLETED',names,flush=True)
