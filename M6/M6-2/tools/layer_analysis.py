import argparse
import csv
import json
import sys
from pathlib import Path
import cv2
import numpy as np
import onnx
import onnxruntime as ort
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'common'))
from runtime import preprocess,image_files


def expose(model,names,out):
    graph=onnx.shape_inference.infer_shapes(onnx.load(model)); values={v.name:v for v in list(graph.graph.value_info)+list(graph.graph.output)}
    for name in names: graph.graph.output.append(values.get(name,onnx.helper.make_tensor_value_info(name,onnx.TensorProto.FLOAT,None)))
    onnx.save(graph,str(out)); options=ort.SessionOptions(); options.intra_op_num_threads=2; options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    return ort.InferenceSession(str(out),sess_options=options,providers=['CPUExecutionProvider'])


def main():
    p=argparse.ArgumentParser(); p.add_argument('--fp32',required=True); p.add_argument('--int8',required=True); p.add_argument('--data',required=True); p.add_argument('--out',required=True); a=p.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    fp=onnx.load(a.fp32); quant=onnx.load(a.int8); quant_names={v for n in quant.graph.node for v in n.output}
    names=[n.output[0] for n in fp.graph.node if n.op_type in ('Conv','MatMul') and n.output[0] in quant_names]
    left=expose(a.fp32,names,out/'fp32_debug.onnx'); right=expose(a.int8,names,out/'int8_debug.onnx')
    metrics={n:[] for n in names}
    for f in image_files(a.data)[:3]:
        tensor=preprocess(cv2.imread(str(f)))[0]; xs=left.run(names,{'images':tensor}); ys=right.run(names,{'images':tensor})
        for n,x,y in zip(names,xs,ys):
            x=x.ravel().astype(np.float64); y=y.ravel().astype(np.float64); cos=float(np.dot(x,y)/max(1e-12,np.linalg.norm(x)*np.linalg.norm(y)))
            lo,hi=min(x.min(),y.min()),max(x.max(),y.max()); edges=np.linspace(lo,hi+1e-10,129)
            px=np.histogram(x,edges)[0]+1e-6; py=np.histogram(y,edges)[0]+1e-6; px=px/px.sum(); py=py/py.sum()
            metrics[n].append([cos,float((px*np.log(px/py)).sum()),float(np.abs(x-y).max()),float(x.min()),float(x.max())])
    rows=[]
    for n,values in metrics.items():
        average=np.mean(values,axis=0); rows.append(dict(layer=n,cosine_similarity=average[0],kl_divergence=average[1],max_absolute_error=max(v[2] for v in values),fp_min=min(v[3] for v in values),fp_max=max(v[4] for v in values),quantized=True))
    with (out/'quant_analysis.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    fig,ax=plt.subplots(figsize=(10,max(5,len(rows)*.13))); data=np.array([[r['cosine_similarity'],r['kl_divergence']] for r in rows]); ax.imshow(data,aspect='auto',cmap='viridis'); ax.set_yticks(range(len(rows)),[r['layer'] for r in rows],fontsize=5); ax.set_xticks([0,1],['CosSim','KL']); fig.tight_layout(); fig.savefig(out/'heatmap.png',dpi=160); plt.close(fig)
    worst=min(rows,key=lambda r:r['cosine_similarity']); (out/'worst_layer.json').write_text(json.dumps(dict(worst=worst,layers=len(rows),samples=min(3,len(image_files(a.data))),scope='indoor numerical discrepancy; causal attribution requires calibration-distribution comparison'),indent=2)); print(json.dumps(worst))


if __name__=='__main__': main()
