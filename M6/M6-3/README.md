# M6-3：会话调优与尾延迟

```bash
.venv-model/bin/python M6/M6-3/tune/session_sweep.py --model M6/M6-1/models/best_fp32.onnx --source hardware/k230/smartcar_usb_20261116_200340 --out M6/M6-3/results
```

图优化、intra/inter线程、内存pattern、CPU arena、执行模式均相对同一个baseline只改一个参数；每组10次预热后100帧，CSV保留全部设置及分位数。再用选中配置测1000帧，保留逐帧pre/core/post/total和直方图/CDF，不能只报均值。

VM实测1000帧P50约43.38ms、P95约48.01ms、P99约50.18ms、最大97.21ms。P95<35、P99<50、max<80三条均不能写成已过。P95主要落在推理本体（约46.6ms），pre/post各约1ms；这是阶段归因证据，不能仅据此声称已经证明某个GPU kernel导致抖动。

CPU EP的60秒基准已完成；CUDA与TensorRT EP在本VM不可用。runtime.Detector提供固定GPU OrtValue地址、IOBinding和enable_cuda_graph入口，CPU模式禁止误开。**CUDA Graph仍未在硬件上执行**：需要Orin上的CUDA EP、固定shape专用模型、检查所有节点分区、排除首次捕获、对比1000帧尾延迟。当前实现捕获对象是ONNX模型体；CPU OpenCV预/后处理不属于CUDA Graph，完整GPU预处理→推理→后处理还需板端适配，不能提前宣称完成。

动态batch导出是通用部署模型；Graph捕获必须使用固定尺寸/地址的专用会话，不能在捕获后换shape。NMS/后处理是否上GPU须在板上测真实代价，不凭桌面CPU结果推荐。
