# 来源与版本

- 培训题面及原始车辆模型：[Blake-John/22SmartCar](https://github.com/Blake-John/22SmartCar)，检出提交 `cdc8dd45296f4eaf57924c0686d861e07252905d`。保留原模型和控制器配置副本，修改点另记。
- 官方 YOLOv8n COCO 预训练权重：[Ultralytics v8.3.0 asset](https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt)，导出工具 Ultralytics 8.3.49、PyTorch 2.6.0+cpu；相关模型按 [Ultralytics 许可](https://www.ultralytics.com/license) 使用。权重和 ONNX SHA256 写入 model_info.yaml。不能把 COCO 模型描述成训练好的赛道模型。
- ONNX 1.17.0、ONNX Runtime 1.20.1：[量化接口](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html)、[CUDA Graph 约束](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html#using-cuda-graphs-preview)。
- MNN 3.2.0：[官方 Python 推理与转换接口](https://mnn-docs.readthedocs.io/en/latest/inference/python.html)，Apache-2.0。此处实际执行的是 VMware x86 CPU 运行时，不冒充 Orin TensorRT 性能。
- Vosk 0.3.45 + [官方中文 small-cn-0.22 模型](https://alphacephei.com/vosk/models)，离线运行。
- nlohmann/json 使用 Ubuntu 系统头文件，不将第三方源码行数计入聚合器自己的实现；自有 C++ 核心约112行，Python exec包装约5行，单 ROS 节点、单进程。实现方式为Python入口加原生聚合器。
- Gazebo classic 11、ROS2 Humble、ackermann_steering_controller 2.54.0。所有速度/精度数据均注明实际执行平台。
