# M6-1：ONNX 导出与独立推理

当前Orin Nano未到货、没有赛道权重/标注测试集。使用官方YOLOv8n COCO权重，只验证工程链路，不声称赛道识别精度达标。

```bash
bash scripts/prepare_models.sh
.venv-model/bin/python M6/M6-1/export_onnx.py --weights M6/M6-1/models/yolov8n.pt --out M6/M6-1/models/best_fp32.onnx --data hardware/k230/smartcar_usb_20261116_200340
.venv-deploy/bin/python M6/M6-1/infer.py --model M6/M6-1/models/best_fp32.onnx --device cpu --source 图片目录 --out detections.json
```

导出使用torch.onnx.export、opset17、动态batch。onnx.checker通过，3张K230实拍对比CosSim>.99，batch=2输出[2,84,2100]已实际验证；完整误差和框结果在results/consistency.json。加载官方可信PyTorch权重时显式处理2.6的weights_only变化，仅导出脚本使用训练框架；runtime.py、infer.py和板端部署包不导入torch/tensorflow。model_info.yaml保存输入、输出、算子、类别和SHA256。

预处理一致性：输入BGR JPEG解码后转RGB；保持宽高比letterbox到320×320，pad=114、INTER_LINEAR、半像素padding采用round(±0.1)；转NCHW float32再/255。输出是[batch,84,2100]，前4行为像素xywh，其后80个类别分数，**没有独立objectness项**。后处理按类别分别NMS，去padding后映射回原图并clip。Windows中文路径使用fromfile+imdecode。

device=cpu/gpu/npu都检查实际EP；GPU为CUDAExecutionProvider，TensorRT也是GPU运行时，不冒充NPU。缺少所选EP立即报错，不把CPU回退的速度填进GPU/NPU栏。VM当前只有CPU和Azure EP；Windows RTX5080没有通过VMware虚拟显卡变成Ubuntu CUDA设备。

连续60秒VM CPU回放基准：1450帧、24.15FPS、P50约41.26ms、P95约49.22ms，峰值RSS118.3MB；排除冷启动和11次预热，冷启动约44ms。此为CPU功能基准，不是Orin成绩。

真实USB摄像头最终录像：406帧、板端时间跨度64.797秒、接收墙钟跨度约65.46秒，正常收到DONE，无传输队列丢弃。录像明确标注CPU/USB；`--rotate180`修正相机安装方向并写入元数据。约6.25FPS受当前USB采集实现限制，不用文件回放FPS代替物理相机吞吐。视频及室内照片留本地，Git只收代码和非媒体结果。

Orin到货后先记录JetPack/驱动/ORT版本并确认EP，再选择匹配aarch64运行时；不要盲装桌面CUDA wheel。使用干净推理环境自验和60秒实测，GPU/NPU不支持的项目保留明确原因。部署包及跨Windows/Ubuntu自验见M5-4/results/cross_system。
