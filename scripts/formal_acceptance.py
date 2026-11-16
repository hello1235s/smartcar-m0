import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[1]; python=str(ROOT/'.venv-ros/bin/python')
def run(script,log):
    with (ROOT/'preparation-logs'/log).open('w') as stream: subprocess.run([python,str(ROOT/'scripts'/script)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
stream=(ROOT/'preparation-logs/terminal-accepted.log').open('w')
process=subprocess.Popen(['bash','scripts/start_terminal.sh','--no-browser'],cwd=ROOT,env=dict(os.environ,SMARTCAR_SOFTWARE_DEMO='1',ROS_DOMAIN_ID='68'),stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+30
while time.monotonic()<deadline:
    try:
        with urllib.request.urlopen('http://127.0.0.1:8081/api/state',timeout=2) as response: state=json.load(response)
        if state.get('perception',{}).get('pid'): break
    except OSError: pass
    if process.poll() is not None: raise RuntimeError('Terminal launcher exited; see terminal-accepted.log')
    time.sleep(.2)
else: raise RuntimeError('Terminal did not become ready')
run('test_hot_switch.py','accepted-hot-switch.log')
run('run_software_experiments.py','accepted-five-experiments.log')
run('test_soft_reset.py','accepted-soft-reset.log')
run('run_fault_case.py','accepted-fault-case.log')
names=json.loads((ROOT/'M5/experiments/latest.json').read_text())['experiments']
subprocess.run([python,str(ROOT/'M5/M5-4/exp.py'),'promote','--name',names[0],'--to',str(ROOT/'M5/baseline/scene_race.yaml')],cwd=ROOT,check=True)
run('finalize_reports.py','accepted-reports.log')
print('FORMAL_ACCEPTANCE_PASS',names,flush=True)
