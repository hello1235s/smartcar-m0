import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import torch
import onnx
import onnxruntime as ort
import yaml
from ultralytics import YOLO
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'common'))
from runtime import preprocess, decode, image_files
import cv2


def main():
    p=argparse.ArgumentParser(); p.add_argument('--weights',required=True); p.add_argument('--out',required=True); p.add_argument('--data',required=True); p.add_argument('--opset',type=int,default=17)
    a=p.parse_args()
    if a.opset!=17: p.error('Assignment requires opset 17')
    # Only accept the reviewed official release downloaded in this workspace.
    original=torch.load
    def trusted_load(*args,**kwargs): kwargs['weights_only']=False; return original(*args,**kwargs)
    torch.load=trusted_load
    try: yolo=YOLO(a.weights)
    finally: torch.load=original
    model=yolo.model.eval().fuse(); torch.set_num_threads(2)
    head=model.model[-1]; head.export=True; head.format='onnx'; head.dynamic=False
    example=torch.zeros(1,3,320,320)
    with torch.no_grad(): model(example)
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    torch.onnx.export(model,example,str(out),opset_version=17,input_names=['images'],output_names=['output0'],dynamic_axes={'images':{0:'batch'},'output0':{0:'batch'}},do_constant_folding=True)
    graph=onnx.load(str(out)); onnx.checker.check_model(graph)
    session=ort.InferenceSession(str(out),providers=['CPUExecutionProvider']); results=[]
    images=image_files(a.data)[:10]
    for f in images:
        image=cv2.imread(str(f)); tensor,transform=preprocess(image)
        with torch.no_grad(): expected=model(torch.from_numpy(tensor)).numpy()
        actual=session.run(None,{'images':tensor})[0]
        cos=float(np.dot(expected.ravel(),actual.ravel())/(np.linalg.norm(expected)*np.linalg.norm(actual)))
        left=decode(expected,image.shape,transform); right=decode(actual,image.shape,transform)
        results.append(dict(file=str(f),cosine_similarity=cos,max_absolute_error=float(np.abs(actual-expected).max()),torch_detections=left,onnx_detections=right,count_equal=len(left)==len(right)))
    assert results and min(x['cosine_similarity'] for x in results)>.99
    batch=session.run(None,{'images':np.repeat(tensor,2,axis=0)})[0]
    assert batch.shape[0]==2
    info=dict(source='official Ultralytics YOLOv8n COCO, v8.3.0 asset',purpose='indoor functional validation; NOT race-trained',weights_sha256=hashlib.sha256(Path(a.weights).read_bytes()).hexdigest(),onnx_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),input=dict(name='images',shape=['batch',3,320,320],dtype='float32',layout='RGB_NCHW',normalization='/255',letterbox=114),output=dict(name='output0',shape=['batch',84,2100],format='xywh_pixels + 80 class scores; no objectness'),opset=17,operators=sorted(set(n.op_type for n in graph.graph.node)),classes=yolo.names)
    out.with_name('model_info.yaml').write_text(yaml.safe_dump(info,allow_unicode=True,sort_keys=False))
    dest=out.parent.parent/'results'; dest.mkdir(exist_ok=True)
    report=dict(tests=results,dynamic_batch_2_shape=list(batch.shape),checker='PASS',qualification='VM functional test only')
    (dest/'consistency.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))


if __name__=='__main__': main()
