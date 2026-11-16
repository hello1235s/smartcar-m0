import argparse
import csv
import json
import sys
import time
from pathlib import Path
import cv2
import numpy as np
import onnxruntime as ort
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'common'))
from runtime import Detector,image_files


def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--source',required=True); p.add_argument('--out',required=True); a=p.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    cv2.setNumThreads(1); image=cv2.imread(str(image_files(a.source)[0]))
    baseline=dict(threads=2,inter_threads=1,graph='all',mem_pattern=True,cpu_arena=True,execution_mode='sequential')
    alternatives=[('baseline',{}),('graph_none',{'graph':'none'}),('graph_basic',{'graph':'basic'}),('intra_1',{'threads':1}),('intra_4',{'threads':4}),('inter_2',{'inter_threads':2}),('mem_off',{'mem_pattern':False}),('arena_off',{'cpu_arena':False}),('parallel',{'execution_mode':'parallel'})]; rows=[]
    for name,change in alternatives:
        config={**baseline,**change}; assert sum(config[k]!=baseline[k] for k in baseline)<=1
        detector=Detector(a.model,**config)
        for _ in range(10): detector.infer(image)
        lat=[]
        for _ in range(100): _,timing=detector.infer(image); lat.append(timing['total_ms'])
        rows.append(dict(experiment=name,changed_parameter=next(iter(change),'none'),**config,p50_ms=float(np.percentile(lat,50)),p95_ms=float(np.percentile(lat,95)),p99_ms=float(np.percentile(lat,99)),fps=100000/sum(lat)))
    with (out/'session_sweep.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    winner=min(rows,key=lambda r:r['p95_ms']); config={k:winner[k] for k in baseline}; detector=Detector(a.model,**config)
    for _ in range(10): detector.infer(image)
    raw=[]
    for i in range(1000): _,timing=detector.infer(image); raw.append(dict(frame=i,**timing))
    with (out/'latency_raw.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(raw[0])); w.writeheader(); w.writerows(raw)
    lat=np.array([r['total_ms'] for r in raw]); fig,axes=plt.subplots(1,2,figsize=(10,4)); axes[0].hist(lat,bins=40,color='#147d92'); axes[0].set(xlabel='End-to-end latency (ms)',ylabel='Frames',title='1000 measured VM CPU frames'); axes[1].plot(np.sort(lat),np.arange(1,len(lat)+1)/len(lat)); axes[1].set(xlabel='Latency (ms)',ylabel='CDF',ylim=(0,1)); fig.tight_layout(); fig.savefig(out/'latency_stability.png',dpi=160); fig.savefig(out/'latency_stability.pdf'); plt.close(fig)
    unavailable={d:str(ort.get_available_providers()) for d in ['CUDAExecutionProvider','TensorrtExecutionProvider'] if d not in ort.get_available_providers()}
    report=dict(hardware='VMware CPU only, not Orin',baseline=baseline,tuned_config=config,frames=1000,p50_ms=float(np.percentile(lat,50)),p95_ms=float(np.percentile(lat,95)),p99_ms=float(np.percentile(lat,99)),max_ms=float(lat.max()),pre_p95_ms=float(np.percentile([r['pre_ms'] for r in raw],95)),core_p95_ms=float(np.percentile([r['core_ms'] for r in raw],95)),post_p95_ms=float(np.percentile([r['post_ms'] for r in raw],95)),cuda_graph_status='PENDING real CUDA provider; runtime includes fixed-buffer IOBinding implementation',unavailable=unavailable,pass_on_orin=None)
    (out/'tuned.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))


if __name__=='__main__': main()
