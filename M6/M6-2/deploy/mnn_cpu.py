import argparse
import json
import sys
import time
from pathlib import Path
import cv2
import MNN
import numpy as np
import onnxruntime as ort
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'common'))
from runtime import preprocess,decode,image_files


def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--onnx',required=True); p.add_argument('--source',required=True); p.add_argument('--out',required=True); p.add_argument('--seconds',type=float,default=60); a=p.parse_args()
    image=cv2.imread(str(image_files(a.source)[0])); tensor=preprocess(image)[0]
    interpreter=MNN.Interpreter(a.model); session=interpreter.createSession({'backend':'CPU','numThread':2,'precision':'high'})
    input_tensor=interpreter.getSessionInput(session); interpreter.resizeTensor(input_tensor,(1,3,320,320)); interpreter.resizeSession(session)
    def infer(current):
        host=MNN.Tensor(current.shape,MNN.Halide_Type_Float,current,MNN.Tensor_DimensionType_Caffe); input_tensor.copyFrom(host); interpreter.runSession(session)
        output=interpreter.getSessionOutput(session); copy=MNN.Tensor(output.getShape(),MNN.Halide_Type_Float,MNN.Tensor_DimensionType_Caffe); output.copyToHostTensor(copy)
        return np.asarray(copy.getData(),np.float32).reshape(copy.getShape())
    actual=infer(tensor); expected=ort.InferenceSession(a.onnx,providers=['CPUExecutionProvider']).run(None,{'images':tensor})[0]
    cosine=float(np.dot(actual.ravel(),expected.ravel())/(np.linalg.norm(actual)*np.linalg.norm(expected)))
    for _ in range(10): infer(tensor)
    start=time.perf_counter(); lat=[]
    while time.perf_counter()-start<a.seconds:
        frame_start=time.perf_counter(); current,transform=preprocess(image); result=infer(current); decode(result,image.shape,transform); lat.append((time.perf_counter()-frame_start)*1000)
    report=dict(backend='MNN 3.2.0 CPU on VMware x86_64; NOT an Orin accelerator result',timing_scope='preprocess + CPU inference and host IO + same NMS',frames=len(lat),seconds=time.perf_counter()-start,cosine_similarity_vs_ort=cosine,max_absolute_error=float(np.abs(actual-expected).max()),p50_ms=float(np.percentile(lat,50)),p95_ms=float(np.percentile(lat,95)),fps=len(lat)/(time.perf_counter()-start),model_bytes=Path(a.model).stat().st_size,map=None)
    Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2)); assert cosine>.99


if __name__=='__main__': main()
