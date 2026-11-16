import argparse
import csv
import json
from pathlib import Path
import statistics
import struct
import time
from mcap.reader import make_reader
KEY_TOPICS=['/dashboard/metrics','/dashboard/faults','/dashboard/task_state','/task/result','/operator/switch','/referee/status','/task/cancel_navigation','/operator/fallback','/operator/fallback_cost']


def records(path):
    with Path(path).open('rb') as f:
        for schema,channel,message in make_reader(f).iter_messages(topics=KEY_TOPICS):
            # std_msgs/String CDR LE: encapsulation4, length4, UTF8 terminated.
            if len(message.data)<9 or message.data[1]!=1: raise ValueError('Unsupported or damaged CDR encoding')
            length=struct.unpack_from('<I',message.data,4)[0]
            if length<=0 or length>len(message.data)-8: raise ValueError('Damaged CDR string')
            value=json.loads(message.data[8:8+length-1]); yield channel.topic,message.log_time,value


def review(run):
    start=time.perf_counter(); run=Path(run); report=json.loads((run/'task_report.json').read_text()) if (run/'task_report.json').exists() else dict(result='UNKNOWN',total_elapsed_s=None,steps=[])
    metrics=[]; faults=[]; actions=[]; clocks=[]
    for topic,stamp,value in records(run/'blackbox.mcap'):
        payload=value['payload']; clocks.append(dict(log_wall_ns=stamp,record_wall_ns=value['wall_ns'],ros_ns=value.get('ros_ns')))
        if topic=='/dashboard/metrics': metrics.append(payload)
        elif topic=='/dashboard/faults': faults.append(payload)
        elif topic in ['/operator/switch','/task/cancel_navigation','/operator/fallback','/operator/fallback_cost']: actions.append(dict(topic=topic,wall_ns=stamp,payload=payload))
    values={}
    for m in metrics:
        for name,v in m.get('topics',{}).items():
            if name.startswith('/perception/'):
                values.setdefault('perception_hz',[]).append(v['hz'])
                if v.get('confidence') is not None: values.setdefault('confidence',[]).append(v['confidence'])
        for key,value in m.get('resources',{}).items():
            if isinstance(value,(int,float)): values.setdefault(key,[]).append(value)
    summary={key:dict(mean=statistics.mean(v),max=max(v)) for key,v in values.items()}
    switches=list(csv.DictReader((run/'switch_log.csv').open())) if (run/'switch_log.csv').exists() else []
    chains=[]
    for fault in faults:
        at=fault.get('stamp_wall_ns',0); cause=str(at)+':'+fault.get('topic',''); later=[x for x in actions if x['payload'].get('cause_id')==cause]
        action=later[0] if later else None
        text='%s on %s (recorded telemetry) → %s → %s'%(fault.get('type'),fault.get('topic','resources'),action['payload'].get('action',action['topic']) if action else 'no causally linked corrective action recorded','handling delay %.3fs; extra navigation cost unmeasured'%((action['wall_ns']-at)/1e9) if action else 'cost unmeasured')
        cost=next((x['payload']['pause_duration_s'] for x in later if x['topic']=='/operator/fallback_cost'),None)
        if cost is not None: text+='; measured task pause %.3fs'%cost
        chains.append(text)
    result=dict(run=str(run.resolve()),result=report['result'],total_elapsed_s=report['total_elapsed_s'],steps=report['steps'],metrics=summary,faults=faults,switches=switches,causal_chains=chains,clock_alignment='MCAP log_time and FSM ts_ns are wall nanoseconds. ros_ns is stored separately; never directly subtract simulation time from wall time.',parsed_messages=len(clocks),review_seconds=time.perf_counter()-start)
    return result


def render(result,previous=None):
    text=['# Run review',str(result['run']),'','Result: **%s**; elapsed: %s s'%(result['result'],result['total_elapsed_s']),'','| Step | Status | Seconds | Retries | Degraded |','|---|---|---:|---:|---|']
    for step in result['steps']: text.append('|{name}|{status}|{elapsed_s:.3f}|{retries}|{degraded}|'.format(**step))
    text+=['','## Key metrics','|Metric|Mean|Peak|','|---|---:|---:|']
    for key,v in result['metrics'].items(): text.append('|%s|%.3f|%.3f|'%(key,v['mean'],v['max']))
    text+=['','## Evidence chain']+(result['causal_chains'] or ['No recorded fault; no root cause inferred.'])+['','## Clock alignment',result['clock_alignment']]
    if previous:
        text+=['','## Previous run comparison','Previous: '+previous['run']]
        for key,v in result['metrics'].items():
            if key in previous['metrics']: text.append('%s mean change: %+.4f'%(key,v['mean']-previous['metrics'][key]['mean']))
        new={f.get('type') for f in result['faults']}-{f.get('type') for f in previous['faults']}; gone={f.get('type') for f in previous['faults']}-{f.get('type') for f in result['faults']}
        text+=['New faults: '+str(sorted(new)), 'Disappeared faults: '+str(sorted(gone)), 'Current switches: '+json.dumps(result['switches'])]
    text+=['','Parse time: %.3f s; %d key messages. Missing metrics remain unavailable.'%(result['review_seconds'],result['parsed_messages'])]
    return '\n'.join(text)+'\n'


def main():
    p=argparse.ArgumentParser(); p.add_argument('run'); p.add_argument('--previous'); a=p.parse_args()
    try:
        run=Path(a.run); result=review(run); previous=None
        candidates=sorted([p for p in run.parent.iterdir() if p.is_dir() and p.name<run.name and (p/'blackbox.mcap').exists()])
        if a.previous or candidates: previous=review(Path(a.previous) if a.previous else candidates[-1])
        (run/'review.md').write_text(render(result,previous),encoding='utf-8'); (run/'review.json').write_text(json.dumps(result,indent=2))
        print('%s | %s s | review %.3f s'%(result['result'],result['total_elapsed_s'],result['review_seconds']))
        for chain in result['causal_chains'][:3]: print(chain)
    except Exception as error: p.exit(2,'Cannot review run: '+str(error)+'; preserve original files and repair/re-export the MCAP.\n')


if __name__=='__main__': main()
