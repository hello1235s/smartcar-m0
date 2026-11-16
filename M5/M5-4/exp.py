import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
import urllib.request
import yaml
from quick_review import review,render
ROOT=Path(__file__).resolve().parents[2]; EXP=ROOT/'M5/experiments'


def merge(base,diff):
    value=copy.deepcopy(base)
    for k,v in diff.items(): value[k]=merge(value.get(k,{}),v) if isinstance(v,dict) else v
    return value
def api(action,**values):
    req=urllib.request.Request('http://127.0.0.1:8081/api/command',data=json.dumps(dict(action=action,**values)).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as f: return json.load(f)
def state():
    with urllib.request.urlopen('http://127.0.0.1:8081/api/state',timeout=3) as f: return json.load(f)
def config(name):
    folder=EXP/name; metadata=json.loads((folder/'metadata.json').read_text()); return folder,metadata,merge(yaml.safe_load(Path(metadata['base']).read_text()),yaml.safe_load((folder/'diff.yaml').read_text()))


def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='action',required=True)
    new=sub.add_parser('new'); new.add_argument('--name',required=True); new.add_argument('--base',required=True); new.add_argument('--set',action='append',default=[]); new.add_argument('--desc',required=True)
    run=sub.add_parser('run'); run.add_argument('--name',required=True); run.add_argument('--runs',type=int,default=3); run.add_argument('--model')
    compare=sub.add_parser('compare'); compare.add_argument('--names',required=True); compare.add_argument('--metric',default='success_rate,elapsed_s')
    promote=sub.add_parser('promote'); promote.add_argument('--name',required=True); promote.add_argument('--to',required=True)
    a=p.parse_args(); EXP.mkdir(exist_ok=True)
    if a.action=='new':
        if Path(a.name).name!=a.name: p.error('Experiment name must be one directory component')
        folder=EXP/a.name; folder.mkdir(); diff={}
        for value in a.set:
            key,raw=value.split('=',1); target=diff; keys=key.split('.')
            for k in keys[:-1]: target=target.setdefault(k,{})
            target[keys[-1]]=yaml.safe_load(raw)
        (folder/'diff.yaml').write_text(yaml.safe_dump(diff)); (folder/'metadata.json').write_text(json.dumps(dict(name=a.name,base=str(Path(a.base).resolve()),description=a.desc,created_ns=time.time_ns()),indent=2))
    elif a.action=='run':
        folder,meta,params=config(a.name); reports=[]
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        model=Path(a.model) if a.model else ROOT/'M6/M6-1/models/best_fp32.onnx'; digest=hashlib.sha256(model.read_bytes()).hexdigest()
        for i in range(a.runs):
            api('NEW_RUN'); api('CLEAR_ESTOP'); api('SET_EXPERIMENT',name=a.name); api('LOAD_MODEL',path=str(model)); api('SET_PARAMS',values=params); before=state(); api('START'); deadline=time.monotonic()+90
            path=Path(before['run'])
            while not (path/'task_report.json').exists() and time.monotonic()<deadline: time.sleep(.2)
            if not (path/'task_report.json').exists(): api('STOP'); raise TimeoutError('Actual task did not finish')
            api('STOP'); api('SEAL_RUN')
            result=review(path); (path/'review.md').write_text(render(result),encoding='utf-8'); (path/'review.json').write_text(json.dumps(result,indent=2)); reports.append(result)
        durations=[r['total_elapsed_s'] for r in reports]; summary=dict(name=a.name,runs=len(reports),successes=sum(r['result']=='SUCCESS' for r in reports),success_rate=sum(r['result']=='SUCCESS' for r in reports)/len(reports),elapsed_s=statistics.mean(durations),elapsed_variance=statistics.variance(durations) if len(durations)>1 else 0,git_commit=commit,model_sha256=digest,params=params,run_paths=[r['run'] for r in reports],scope='software Mock task, actual ROS+MCAP transport')
        (folder/'summary.json').write_text(json.dumps(summary,indent=2)); print(json.dumps(summary,indent=2))
    elif a.action=='compare':
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        summaries=[json.loads((EXP/n/'summary.json').read_text()) for n in a.names.split(',')]; metrics=a.metric.split(','); table=['|Experiment|'+'|'.join(metrics)+'|','|---|'+'---:|'*len(metrics)]
        for s in summaries: table.append('|'+s['name']+'|'+'|'.join(str(s.get(m,'unavailable')) for m in metrics)+'|')
        (EXP/'comparison.md').write_text('\n'.join(table)); fig=make_subplots(rows=1,cols=len(metrics),subplot_titles=metrics)
        for i,m in enumerate(metrics): fig.add_trace(go.Bar(name=m,x=[s['name'] for s in summaries],y=[s.get(m) for s in summaries]),row=1,col=i+1)
        fig.update_layout(title='Actual software experiments; each metric has its own axis',showlegend=False); fig.write_html(str(EXP/'comparison.html'),include_plotlyjs=True)
    else:
        folder,meta,params=config(a.name); target=Path(a.to).resolve()
        if ROOT not in target.parents: p.error('Promotion target must be inside repository')
        relative=str(target.relative_to(ROOT)); dirty=subprocess.check_output(['git','status','--porcelain','--',relative],cwd=ROOT,text=True)
        if dirty.strip(): p.error('Promotion target has uncommitted changes; refusing overwrite')
        summary=json.loads((folder/'summary.json').read_text())
        if summary['success_rate']<.6: p.error('Experiment does not meet success threshold')
        target.parent.mkdir(parents=True,exist_ok=True); target.write_text(yaml.safe_dump(params)); manifest=target.with_suffix('.manifest.json'); manifest.write_text(json.dumps(summary,indent=2))
        # Only these two reviewed files enter this commit; existing M0 changes remain excluded.
        subprocess.run(['git','add','--',relative,str(manifest.relative_to(ROOT))],cwd=ROOT,check=True)
        staged=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).splitlines()
        allowed={relative,str(manifest.relative_to(ROOT))}
        if set(staged)-allowed: p.error('Unrelated files already staged; refusing commit')
        subprocess.run(['git','commit','-m','Promote '+a.name+'; actual success '+str(summary['success_rate'])],cwd=ROOT,check=True)


if __name__=='__main__': main()
