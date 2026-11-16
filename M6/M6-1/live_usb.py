"""Real USB camera to CPU ORT to annotated recording, no training framework."""
import argparse
import base64
import json
import socket
import sys
import time
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'common'))
from runtime import Detector


def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--relay',default='127.0.0.1:8766'); p.add_argument('--out',required=True); p.add_argument('--seconds',type=float,default=90); p.add_argument('--rotate180',action='store_true'); a=p.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True); detector=Detector(a.model); host,port=a.relay.rsplit(':',1); deadline=time.monotonic()+a.seconds; rows=[]; completed=False; writer=None; first=None; connection=None
    try:
      while time.monotonic()<deadline and not completed:
        try: connection=socket.create_connection((host,int(port)),timeout=2)
        except OSError: time.sleep(.1); continue
        connection.settimeout(30)
        with connection.makefile('rb') as stream:
            for line in stream:
                if time.monotonic()>deadline: break
                e=json.loads(line)
                if e['kind']=='done': completed=True; break
                if e['kind']!='video': continue
                frame=cv2.imdecode(np.frombuffer(base64.b64decode(e['data']),np.uint8),cv2.IMREAD_COLOR)
                if a.rotate180: frame=cv2.rotate(frame,cv2.ROTATE_180)
                detections,timing=detector.infer(frame); now=time.monotonic(); first=first or now
                for d in detections:
                    x1,y1,x2,y2=map(int,d['xyxy']); cv2.rectangle(frame,(x1,y1),(x2,y2),(30,220,100),1)
                    cv2.putText(frame,'%d %.2f'%(d['class_id'],d['confidence']),(x1,max(12,y1)),cv2.FONT_HERSHEY_SIMPLEX,.35,(30,220,100),1)
                cv2.putText(frame,'K230 USB | CPU | %.1f fps'%(len(rows)/max(.001,now-first)),(6,18),cv2.FONT_HERSHEY_SIMPLEX,.4,(240,240,240),1)
                if writer is None: writer=cv2.VideoWriter(str(out/'usb_cpu_demo.avi'),cv2.VideoWriter_fourcc(*'MJPG'),6.25,(frame.shape[1],frame.shape[0]))
                writer.write(frame); rows.append(dict(board_ticks_ms=e['board_ticks_ms'],receipt_wall_ns=time.time_ns(),detections=detections,**timing))
                if len(rows) in (1,120,300): cv2.imwrite(str(out/('frame_%04d.jpg'%len(rows))),frame)
        if connection: connection.close()
        if rows and not completed: raise RuntimeError('USB stream ended before DONE; interrupted capture is not qualified')
        if not completed: time.sleep(.1)
    finally:
        connection.close()
        if writer: writer.release()
    report=dict(source='real K230 USB camera, CPU ORT on VMware; not board inference',rotation_degrees=180 if a.rotate180 else 0,completed=completed,received_frames=len(rows),wall_span_s=time.monotonic()-first if first else 0,board_span_s=(rows[-1]['board_ticks_ms']-rows[0]['board_ticks_ms'])/1000 if len(rows)>1 else 0,p95_infer_ms=float(np.percentile([r['total_ms'] for r in rows],95)) if rows else None)
    (out/'live_report.json').write_text(json.dumps(report,indent=2)); (out/'detections.jsonl').write_text('\n'.join(json.dumps(r) for r in rows)); print(json.dumps(report,indent=2))
    assert completed and report['board_span_s']>=60


if __name__=='__main__': main()
