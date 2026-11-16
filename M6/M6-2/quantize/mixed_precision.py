import argparse
import csv
import json
import sys
from pathlib import Path
import cv2
import numpy as np
import onnx
import onnxruntime as ort
from onnxruntime.quantization import quantize_static,QuantFormat,QuantType
sys.path.insert(0,str(Path(__file__).resolve().parent)); from ptq import Reader
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'common')); from runtime import preprocess,image_files


def main():
    p=argparse.ArgumentParser(); p.add_argument('--fp32',required=True); p.add_argument('--analysis',required=True); p.add_argument('--calib',required=True); p.add_argument('--data',required=True); p.add_argument('--out',required=True); a=p.parse_args()
    rows=sorted(csv.DictReader(open(a.analysis)),key=lambda r:float(r['cosine_similarity'])); outputs={r['layer'] for r in rows[:3]}; graph=onnx.load(a.fp32); exclude=[n.name for n in graph.graph.node if any(o in outputs for o in n.output)]
    quantize_static(a.fp32,a.out,Reader(image_files(a.calib)[:500]),quant_format=QuantFormat.QDQ,activation_type=QuantType.QUInt8,weight_type=QuantType.QUInt8,op_types_to_quantize=['Conv','MatMul'],nodes_to_exclude=exclude)
    options=ort.SessionOptions(); options.intra_op_num_threads=2; left=ort.InferenceSession(a.fp32,sess_options=options,providers=['CPUExecutionProvider']); right=ort.InferenceSession(a.out,sess_options=options,providers=['CPUExecutionProvider']); tests=[]
    for f in image_files(a.data)[:3]:
        x=preprocess(cv2.imread(str(f)))[0]; fp=left.run(None,{'images':x})[0]; quant=right.run(None,{'images':x})[0]; u,v=fp.astype(np.float64).ravel(),quant.astype(np.float64).ravel()
        tests.append(dict(file=f.name,output_cosine_similarity=float(np.dot(u,v)/(np.linalg.norm(u)*np.linalg.norm(v))),max_absolute_error=float(np.abs(fp-quant).max())))
    result=dict(excluded_fp32_layers=exclude,reason='Three lowest measured Conv-output cosine similarities, not assumed first/last layers',tests=tests,map=None,map_qualification='Pending independent labeled race data; no QAT accuracy claim')
    Path(a.out).with_suffix('.mixed.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))


if __name__=='__main__': main()
