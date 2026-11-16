"""YOLO txt labels, AP interpolated at 101 recall points, IoU .50:.95."""
import argparse
import csv
import json
import sys
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'common'))
from runtime import Detector,image_files


def iou(box,boxes):
    if not len(boxes): return np.array([])
    a=np.maximum(box[:2],boxes[:,:2]); b=np.minimum(box[2:],boxes[:,2:]); inter=np.prod(np.maximum(0,b-a),1)
    return inter/np.maximum(1e-9,np.prod(box[2:]-box[:2])+np.prod(boxes[:,2:]-boxes[:,:2],1)-inter)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--data',required=True); p.add_argument('--out',required=True); a=p.parse_args()
    root=Path(a.data); files=image_files(root/'images')
    if not files: p.error('Missing images/; mAP remains unmeasured, not zero')
    detector=Detector(a.model); detector.conf=.001; gt={}; detections=[]; counts={}
    for index,f in enumerate(files):
        label=root/'labels'/f.relative_to(root/'images').with_suffix('.txt')
        if not label.exists(): p.error('Missing label '+str(label)+'; cannot report mAP')
        image=cv2.imread(str(f)); h,w=image.shape[:2]; gt[index]={}
        for line in label.read_text().splitlines():
            if not line.strip(): continue
            c,x,y,bw,bh=map(float,line.split()); c=int(c); box=[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]
            gt[index].setdefault(c,[]).append(box); counts[c]=counts.get(c,0)+1
        pred,_=detector.infer(image)
        detections.extend((d['confidence'],index,d['class_id'],d['xyxy']) for d in pred[:300])
    rows=[]
    for c,count in sorted(counts.items()):
        aps=[]
        for threshold in np.arange(.5,.951,.05):
            used={}; tp=[]; fp=[]
            for score,index,label,box in sorted(detections,reverse=True):
                if label!=c: continue
                boxes=np.asarray(gt[index].get(c,[])); overlaps=iou(np.array(box),boxes); hit=False
                for j in np.argsort(-overlaps):
                    if overlaps[j]>=threshold and j not in used.setdefault(index,set()): used[index].add(int(j)); hit=True; break
                tp.append(int(hit)); fp.append(int(not hit))
            tp=np.cumsum(tp); fp=np.cumsum(fp); recall=tp/count; precision=tp/np.maximum(1,tp+fp)
            aps.append(float(np.mean([max(precision[recall>=r],default=0) for r in np.linspace(0,1,101)])))
        rows.append(dict(class_id=c,ground_truth=count,AP50=aps[0],AP50_95=float(np.mean(aps))))
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w') as f:
        writer=csv.DictWriter(f,fieldnames=['class_id','ground_truth','AP50','AP50_95']); writer.writeheader(); writer.writerows(rows)
    print(json.dumps(dict(images=len(files),classes=len(rows),mAP50_95=float(np.mean([r['AP50_95'] for r in rows])) if rows else None)))


if __name__=='__main__': main()
