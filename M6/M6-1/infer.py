import argparse
import json
import sys
from pathlib import Path
import cv2
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'common'))
from runtime import Detector,image_files,read_image


def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--source',required=True); p.add_argument('--device',choices=['cpu','gpu','npu'],default='cpu'); p.add_argument('--out',default='detections.json')
    a=p.parse_args(); detector=Detector(a.model,a.device); results=[]
    for f in image_files(a.source):
        image=read_image(f)
        if image is None: raise ValueError('Cannot read '+str(f))
        detections,timing=detector.infer(image); results.append(dict(file=str(f),detections=detections,timing=timing))
    Path(a.out).write_text(json.dumps(results,indent=2)); print('processed',len(results),'images')


if __name__=='__main__': main()
