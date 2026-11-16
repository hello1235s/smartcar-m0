import argparse
import hashlib
import json
import sys
from pathlib import Path
import cv2
import numpy as np
import onnx
import onnxruntime as ort
from onnxruntime.quantization import CalibrationDataReader,QuantType,QuantFormat,quantize_dynamic,quantize_static,CalibrationMethod
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'common'))
from runtime import preprocess,image_files


class Reader(CalibrationDataReader):
    def __init__(self,files): self.files=files; self.index=0
    def get_next(self):
        if self.index>=len(self.files): return None
        image=cv2.imread(str(self.files[self.index])); self.index+=1
        return {'images':preprocess(image)[0]}


def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--calib',required=True); p.add_argument('--out',required=True); p.add_argument('--functional-indoor',action='store_true'); a=p.parse_args()
    files=image_files(a.calib)[:500]; unique={hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    if not a.functional_indoor: p.error('Race calibration requires a reviewed independent dataset manifest; current script must explicitly use --functional-indoor')
    if not files: p.error('No real calibration images found')
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True); reports=[]
    for mode in ['dynamic','static_qdq','static_qoperator']:
        dest=out/(mode+'.onnx')
        try:
            if mode=='dynamic': quantize_dynamic(a.model,str(dest),weight_type=QuantType.QUInt8,op_types_to_quantize=['Conv','MatMul'])
            else:
                quantize_static(a.model,str(dest),Reader(files),quant_format=QuantFormat.QDQ if mode=='static_qdq' else QuantFormat.QOperator,activation_type=QuantType.QUInt8,weight_type=QuantType.QUInt8,calibrate_method=CalibrationMethod.MinMax,op_types_to_quantize=['Conv','MatMul'],extra_options={'ActivationSymmetric':False,'WeightSymmetric':False})
            graph=onnx.load(str(dest)); onnx.checker.check_model(graph)
            counts={op:sum(n.op_type==op for n in graph.graph.node) for op in ['QuantizeLinear','DequantizeLinear','ConvInteger','QLinearConv','MatMulInteger']}
            if not sum(counts.values()): raise RuntimeError('No operators were quantized')
            opts=ort.SessionOptions(); opts.intra_op_num_threads=2
            session=ort.InferenceSession(str(dest),sess_options=opts,providers=['CPUExecutionProvider'])
            sample=preprocess(cv2.imread(str(files[0])))[0]; result=session.run(None,{'images':sample})[0]
            if not np.isfinite(result).all(): raise RuntimeError('Non-finite quantized output')
            reports.append(dict(mode=mode,status='PASS_functional_only',bytes=dest.stat().st_size,quantized_ops=counts,output_shape=list(result.shape)))
        except Exception as e: reports.append(dict(mode=mode,status='FAILED',error=str(e)))
    report=dict(calibration=dict(files=len(files),unique_hashes=len(unique),source='real K230 USB adjacent indoor frames; NOT race distribution, no labels',race_qualification=False),schemes=reports,map=None,speedup_qualification=None)
    (out.parent/'results').mkdir(exist_ok=True); (out.parent/'results/quantization.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))


if __name__=='__main__': main()
