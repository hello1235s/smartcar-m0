import argparse
import csv
import json
import sys
import threading
import time
from pathlib import Path
import cv2
import numpy as np
import psutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'common'))
from runtime import Detector,preprocess,decode,image_files
from pipeline import Pipeline,Engine


def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--source',required=True); p.add_argument('--threads',type=int,default=3); p.add_argument('--seconds',type=float,default=180); p.add_argument('--out',required=True); a=p.parse_args()
    cv2.setNumThreads(1); detector=Detector(a.model,threads=2); engine=Engine(detector)
    images=[cv2.imread(str(f)) for f in image_files(a.source)[:120]]
    if not images or any(i is None for i in images): p.error('No valid source frames')
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True); proc=psutil.Process(); samples=[]; closed=threading.Event()
    def monitor():
        while not closed.wait(.25): samples.append([time.monotonic(),proc.memory_info().rss/1024**2,proc.cpu_percent()])
    monitor_thread=threading.Thread(target=monitor); monitor_thread.start()
    def source():
        started=time.perf_counter(); i=0
        while time.perf_counter()-started<a.seconds:
            yield images[i%len(images)]; i+=1
    pipe=Pipeline(engine,preprocess,decode); outputs=[]
    def result(frame,detections,record):
        if len(outputs)<3:
            shown=frame.copy()
            for detection in detections:
                x1,y1,x2,y2=map(int,detection['xyxy']); cv2.rectangle(shown,(x1,y1),(x2,y2),(0,255,0),1)
            cv2.imwrite(str(out/('detection_%02d.jpg'%len(outputs))),shown); outputs.append(detections)
    try: report=pipe.run(source(),a.threads,on_result=result)
    finally: closed.set(); monitor_thread.join(3)
    lat=np.array([r['total_ms'] for r in pipe.results]); rss=np.array([s[1] for s in samples]); stable=rss[max(0,min(20,len(rss)-1)):]
    report.update(mode=a.threads,hardware='VMware Ubuntu CPU, not Orin',source='replay of real K230 USB indoor frames',p50_ms=float(np.percentile(lat,50)),p95_ms=float(np.percentile(lat,95)),p99_ms=float(np.percentile(lat,99)),rss_peak_mb=float(rss.max()),rss_warm_range_mb=float(stable.max()-stable.min()),cpu_mean_percent=float(np.mean([s[2] for s in samples])),drops_inside_pipeline=report['produced']-report['consumed'])
    with (out/'latencies.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(pipe.results[0])); w.writeheader(); w.writerows(pipe.results)
    with (out/'rss.csv').open('w') as f: w=csv.writer(f); w.writerow(['steady_t','rss_mb','cpu_percent']); w.writerows(samples)
    (out/'report.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))


if __name__=='__main__': main()
