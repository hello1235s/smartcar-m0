import json
import time
import urllib.request
import urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def api(action):
    req=urllib.request.Request('http://127.0.0.1:8081/api/command',data=json.dumps(dict(action=action)).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=15) as f: return json.load(f)
def state():
    with urllib.request.urlopen('http://127.0.0.1:8081/api/state') as f: return json.load(f)
api('NEW_RUN'); api('CLEAR_ESTOP'); api('START'); time.sleep(3.6); before=state(); api('SOFT_RESET'); after=state()
assert before['pid']==after['pid'] and after['referee']['state']=='RUNNING' and after['referee']['remaining_s']<=before['referee']['remaining_s']
rejected=False
try: api('HARD_RESET')
except urllib.error.HTTPError as e: rejected=e.code==400
assert rejected
run=Path(after['run']); deadline=time.monotonic()+20
while not (run/'task_report.json').exists() and time.monotonic()<deadline: time.sleep(.1)
assert json.loads((run/'task_report.json').read_text())['result']=='SUCCESS'; api('STOP'); api('SEAL_RUN')
report=dict(soft_reset_kept_pid=True,old_pid=before['pid'],new_pid=after['pid'],remaining_before=before['referee']['remaining_s'],remaining_after=after['referee']['remaining_s'],hard_reset_rejected_in_competition=rejected,task_restarted_and_finished=True,run=str(run)); out=ROOT/'evidence/M5-hot-switch/soft_reset.json'; out.write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
