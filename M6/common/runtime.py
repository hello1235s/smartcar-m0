"""Deployment module: no training framework imports."""
import json
import time
from pathlib import Path
import cv2
import numpy as np
import onnxruntime as ort


def read_image(path):
    # OpenCV imread on Windows does not reliably accept Chinese paths.
    return cv2.imdecode(np.fromfile(str(path),dtype=np.uint8),cv2.IMREAD_COLOR)


def preprocess(image, size=320):
    h,w=image.shape[:2]; ratio=min(size/h,size/w)
    nw,nh=round(w*ratio),round(h*ratio); px,py=(size-nw)/2,(size-nh)/2
    image=cv2.resize(image,(nw,nh),interpolation=cv2.INTER_LINEAR)
    image=cv2.copyMakeBorder(image,round(py-.1),round(py+.1),round(px-.1),round(px+.1),cv2.BORDER_CONSTANT,value=(114,114,114))
    return np.ascontiguousarray(image[:,:,::-1].transpose(2,0,1)[None],dtype=np.float32)/255.,(ratio,px,py)


def decode(output, image_shape, transform, conf=.25, iou=.45):
    predictions=output[0].T
    labels=predictions[:,4:].argmax(1); scores=predictions[np.arange(len(predictions)),labels+4]
    keep=scores>=conf; boxes=predictions[keep,:4].copy(); scores=scores[keep]; labels=labels[keep]
    if not len(boxes): return []
    boxes[:,:2]-=boxes[:,2:]/2
    selected=[]
    for label in np.unique(labels):
        ids=np.where(labels==label)[0]; local=cv2.dnn.NMSBoxes(boxes[ids].tolist(),scores[ids].tolist(),conf,iou)
        selected.extend(ids[np.asarray(local,dtype=int).reshape(-1)].tolist())
    ratio,px,py=transform; result=[]
    for i in selected:
        x,y,w,h=boxes[i]; xy=np.array([(x-px)/ratio,(y-py)/ratio,(x+w-px)/ratio,(y+h-py)/ratio])
        xy[[0,2]]=xy[[0,2]].clip(0,image_shape[1]); xy[[1,3]]=xy[[1,3]].clip(0,image_shape[0])
        result.append(dict(class_id=int(labels[i]),confidence=float(scores[i]),xyxy=xy.tolist()))
    return sorted(result,key=lambda d:-d['confidence'])


class Detector:
    def __init__(self, model, device='cpu', threads=2, graph='all', cuda_graph=False, inter_threads=1, mem_pattern=True, cpu_arena=True, execution_mode='sequential'):
        npu=next((p for p in ['CANNExecutionProvider','QNNExecutionProvider','RknpuExecutionProvider'] if p in ort.get_available_providers()),'NoAvailableNPUExecutionProvider')
        providers={'cpu':'CPUExecutionProvider','gpu':'CUDAExecutionProvider','npu':npu}
        if device not in providers: raise ValueError('device must be cpu/gpu/npu')
        selected=providers[device]
        if selected not in ort.get_available_providers():
            raise RuntimeError(selected+' unavailable; available='+str(ort.get_available_providers())+'. No CPU fallback score.')
        options=ort.SessionOptions(); options.intra_op_num_threads=threads; options.inter_op_num_threads=inter_threads
        options.enable_mem_pattern=mem_pattern; options.enable_cpu_mem_arena=cpu_arena
        options.graph_optimization_level={'none':ort.GraphOptimizationLevel.ORT_DISABLE_ALL,'basic':ort.GraphOptimizationLevel.ORT_ENABLE_BASIC,'all':ort.GraphOptimizationLevel.ORT_ENABLE_ALL}[graph]
        options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL if execution_mode=='sequential' else ort.ExecutionMode.ORT_PARALLEL
        if cuda_graph and device!='gpu': raise ValueError('CUDA Graph requires CUDAExecutionProvider')
        provider=(selected,{'enable_cuda_graph':'1'}) if cuda_graph else selected
        self.session=ort.InferenceSession(str(model),sess_options=options,providers=[provider]); self.session.disable_fallback()
        self.input=self.session.get_inputs()[0]; self.names=[o.name for o in self.session.get_outputs()]
        self.size=int(self.input.shape[2]); self.model=str(model); self.conf=.25
        self.cuda_graph=cuda_graph; self.binding=None; self.bound_input=None; self.bound_output=None
        if cuda_graph:
            # Fixed shapes and stable GPU addresses; only the ONNX body is captured.
            shape=[1]+[int(v) for v in self.input.shape[1:]]
            output_shape=[1]+[int(v) for v in self.session.get_outputs()[0].shape[1:]]
            self.bound_input=ort.OrtValue.ortvalue_from_numpy(np.zeros(shape,np.float32),'cuda',0)
            self.bound_output=ort.OrtValue.ortvalue_from_shape_and_type(output_shape,np.float32,'cuda',0)
            self.binding=self.session.io_binding(); self.binding.bind_ortvalue_input(self.input.name,self.bound_input)
            self.binding.bind_ortvalue_output(self.names[0],self.bound_output)

    def raw(self,tensor):
        if self.cuda_graph:
            self.bound_input.update_inplace(tensor); self.session.run_with_iobinding(self.binding)
            return self.binding.copy_outputs_to_cpu()[0]
        return self.session.run(self.names,{self.input.name:tensor})[0]

    def infer(self,image):
        start=time.perf_counter(); confidence=self.conf; tensor,transform=preprocess(image,self.size); pre=time.perf_counter()
        output=self.raw(tensor); core=time.perf_counter(); detections=decode(output,image.shape,transform,confidence)
        end=time.perf_counter()
        return detections,dict(pre_ms=(pre-start)*1000,core_ms=(core-pre)*1000,post_ms=(end-core)*1000,total_ms=(end-start)*1000)


def image_files(source):
    p=Path(source)
    return sorted([f for f in p.rglob('*') if f.suffix.lower() in ('.jpg','.jpeg','.png')]) if p.is_dir() else [p]
