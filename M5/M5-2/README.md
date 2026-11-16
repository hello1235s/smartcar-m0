# M5-2：轻量监控面板

```bash
source scripts/env.sh
# 纯软件训练，默认会自动打开浏览器：
SMARTCAR_SOFTWARE_DEMO=1 bash scripts/start_terminal.sh
# 自动验证：
.venv-ros/bin/python scripts/verify_dashboard.py
```

机器人侧一个原生ROS2聚合节点，Python文件exec进入C++实现，保持同一进程；自有C++约112行，包装约5行。采用原生实现以满足50MB内存约束。话题由topic_patterns参数发现，支持运行时改模式，最多64个订阅；每个匹配话题一个订阅，DDS队列深度1，图像不经过上位机。节点只聚合、降频和判故障，不存储和渲染。

发布 /dashboard/metrics 10Hz，/dashboard/faults事件，/dashboard/task_state原状态镜像。频率按2秒接收窗口，超时阈值0.65秒，低频持续0.3秒降级；资源阈值为CPU>95%、温度>85℃或电压<10.5V。资源话题和事件话题有独立期望频率，任务状态事件不会因为静默被当成传感器掉线。只有源提供单调seq时才计算丢包率；源没有序号、不同钟域、缺传感器的值保持null，不能填0冒充实测。

上位机FastAPI+WebSocket，原生DDS接聚合指标，浏览器5Hz更新；五个固定区域、任务上下文、健康度、故障筛选、裁判和急停。模型通过既有感知进程的ROS参数服务热切，Web进程不加载模型，也不订阅图像。默认缩略图关闭。调试相机须显式运行独立USB/推理演示程序。SDK安装、资源部署在THIRD_PARTY.md及scripts/requirements_ros.txt。

历史在主机内存有界缓存，重连补最近300点；完整已存历史可导出自包含HTML，支持滑块离线回放，浏览器端不依赖CDN。截图/录屏按钮调用浏览器原生共享屏幕选择器，必须由使用者选择要共享的窗口。

最终65秒资源测试：聚合器平均约1.24%单核CPU、23.0MB RSS；Web主机平均约3.42%单核CPU、峰值93.3MB RSS；均满足题目阈值。故障发现约0.7秒，聚合带宽约10KB/s，低于50KB/s。精确值及原始资源曲线见evidence/M5-dashboard最新report.json。测试的资源遥测数值来自明确标注的模拟源，进程CPU/RSS与ROS传输延迟是实际测量。

服务仅绑定127.0.0.1。Windows使用SSH转发访问localhost:8080；手机同屏如需开放监听须自行配置可信网络及认证，当前不自动扩大对外访问范围。
