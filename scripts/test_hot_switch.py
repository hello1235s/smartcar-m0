import json
import time
import urllib.request
import urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def api(action,**args):
    req=urllib.request.Request('http://127.0.0.1:8081/api/command',data=json.dumps(dict(action=action,**args)).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as f: return json.load(f)
def state():
    with urllib.request.urlopen('http://127.0.0.1:8081/api/state') as f: return json.load(f)
deadline=time.monotonic()+20
while True:
    before=state()
    if before.get('perception',{}).get('pid'): break
    if time.monotonic()>deadline: raise RuntimeError('Perception state did not become ready')
    time.sleep(.2)
api('LOAD_MODEL',path=str(ROOT/'M6/M6-1/models/best_fp32.onnx')); first=state()
api('LOAD_MODEL',path=str(ROOT/'M6/M6-2/models/static_qdq.onnx')); second=state()
failed=False
try: api('LOAD_MODEL',path=str(ROOT/'M6/no_such_model.onnx'))
except urllib.error.HTTPError: failed=True
assert failed
after=state(); assert before['pid']==first['pid']==second['pid']==after['pid']
assert before['perception']['pid']==after['perception']['pid']
image=str(ROOT/'M6/M6-1/test_assets/official_bus.jpg')
api('LOAD_MODEL',path=str(ROOT/'M6/M6-1/models/best_fp32.onnx'))
results=[]
for threshold in [.05,.95]:
    api('SET_PARAMS',values=dict(confidence=threshold))
    req=urllib.request.Request('http://127.0.0.1:8081/api/infer',data=json.dumps(dict(image=image)).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req) as f: r=json.load(f); results.append(dict(confidence=threshold,detections=r['detections'],pid=r['pid']))
assert len(results[0]['detections'])>0 and len(results[1]['detections'])<len(results[0]['detections'])
report=dict(pid_before=before['pid'],pid_after=after['pid'],perception_pid_before=before['perception']['pid'],perception_pid_after=after['perception']['pid'],two_real_onnx_models_loaded=True,invalid_model_rejected=True,inference_after_rejection=True,threshold_tests=results)
out=ROOT/'evidence/M5-hot-switch'; out.mkdir(parents=True,exist_ok=True); (out/'report.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
