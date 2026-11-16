import argparse
import csv
import json
import platform
import sys
import time
from pathlib import Path
import cv2
import numpy as np
import psutil
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'common'))
from runtime import Detector,image_files


def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--source',required=True); p.add_argument('--device',default='cpu'); p.add_argument('--seconds',type=float,default=60); p.add_argument('--out',required=True); p.add_argument('--threads',type=int,default=2); p.add_argument('--graph',default='all')
    a=p.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    if a.seconds<60: p.error('Final benchmark must last at least 60 seconds')
    model=Detector(a.model,a.device,a.threads,a.graph); images=[cv2.imread(str(f)) for f in image_files(a.source)[:120]]
    assert images and all(i is not None for i in images)
    cold_start=time.perf_counter(); model.infer(images[0]); cold=(time.perf_counter()-cold_start)*1000
    for _ in range(10): model.infer(images[0])
    proc=psutil.Process(); cpu0=sum(proc.cpu_times()[:2]); start=time.perf_counter(); rows=[]; rss=[]
    while time.perf_counter()-start<a.seconds:
        _,t=model.infer(images[len(rows)%len(images)]); rows.append(t); rss.append(proc.memory_info().rss)
    elapsed=time.perf_counter()-start; cpu=sum(proc.cpu_times()[:2])-cpu0; lat=np.array([r['total_ms'] for r in rows])
    with (out/'latencies.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    report=dict(platform=platform.platform(),hardware='VMware Ubuntu 22.04 CPU; not Orin',source='replay of real K230 indoor USB captures',device=a.device,threads=a.threads,graph=a.graph,frames=len(rows),seconds=elapsed,fps=len(rows)/elapsed,cold_ms=cold,warmup_frames=11,p50_ms=float(np.percentile(lat,50)),p95_ms=float(np.percentile(lat,95)),p99_ms=float(np.percentile(lat,99)),max_ms=float(lat.max()),rss_peak_mb=max(rss)/1024**2,cpu_percent_one_core=100*cpu/elapsed,model_bytes=Path(a.model).stat().st_size)
    (out/'benchmark.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))


if __name__=='__main__': main()
