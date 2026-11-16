import json
import time
import urllib.request
def request(action):
    req=urllib.request.Request('http://127.0.0.1:8081/api/command',data=json.dumps(dict(action=action)).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as f: return json.load(f)
def pid():
    with urllib.request.urlopen('http://127.0.0.1:8081/api/state',timeout=2) as f: return json.load(f)['pid']
old=pid(); request('NEW_RUN'); request('STOP'); print(request('HARD_RESET'),flush=True); deadline=time.monotonic()+30
while time.monotonic()<deadline:
    try:
        new=pid()
        if new!=old: print(json.dumps(dict(hard_reset='PASS_pre_post_competition',old_pid=old,new_pid=new))); break
    except OSError: pass
    time.sleep(.3)
else: raise RuntimeError('Supervisor did not restart terminal')
