# M1 / M3 / M5 / M6 训练交付

作者：张驰。环境：VMware Ubuntu22.04 + ROS2 Humble；K230通过USB接入Windows，再经本机SSH转发进入ROS。K230 Wi-Fi不作为本次流程依赖。Orin Nano尚未到货。

## 当前验收

| 任务 | 当前结果 | 关键证据 |
|---|---|---|
| M1-1 | 已验 | 3节点、自定义接口、滤波、动态参数、服务超时 |
| M1-2 | 已验 | robot1/2六节点、参数隔离、真实就绪后启动 |
| M1-3 | 已验 | 两组K/外参、同步扫参、投影图、TF图、时钟切换录像 |
| M1-4 | 已验 | 31.72FPS、控制约21Hz、P95约26.71ms、像素语义一致 |
| M3-1 | 已验 | 10次圆角2m方形、odom/真值CSV、误差与TF图 |
| M3-2 | 已验 | 12×8m环形世界、标准地图、窄门0.95m、实际历史回访约束 |
| M3-3 | 已验 | 最终3次成功2次，66.7%≥60%，路径>12m并含转弯 |
| M3-4 | 已验 | 3组各10次：A8/10、B3/10、B调优7/10；四指标及失效实验 |
| M5-1 | 已验 | 纯Python内核、30个Mock契约测试、ROS适配接口 |
| M5-2 | 已验 | 聚合器/主机平均CPU约1.24%/3.42%，RSS约23/93MB，10Hz DDS |
| M5-3 | 已验 | 真实USB麦克风/KEY、离线回放、锁存急停、实模型热切与复位 |
| M5-4 | 已验 | 5场真实ROS软件任务、MCAP复盘、实验工具、跨系统基线自验 |
| M6-1 | 工程已验，板端待验 | ONNX17动态batch、独立推理、CPU60s、真实USB录像65s |
| M6-2 | 工程已验，精度/板端指标待补 | 3种PTQ、逐层分析、混合精度、MNN；无赛道标签，CPU仅约1.45倍 |
| M6-3 | CPU已验，CUDA待实现/验收 | 9组单参数与1000帧；CPU尾延迟未达题目阈值，完整GPU Graph仍待板端 |
| M6-4 | 工程已验，板端性能待优化 | 6项线程测试、3方案各180s、0内部丢帧；加速比约1.04，未达1.6 |

M5模拟任务的导航/抓取用明确标记的Mock，不能当成真实小车或机械臂验收。M3是实际Gazebo物理仿真，M6相机演示是实际K230 USB输入在VM CPU推理。板端、赛道mAP以及未达倍率保留待办，不填虚构成绩。

## 使用入口

```bash
cd ~/smartcar-advanced
source scripts/env.sh
# 训练终端（默认自动开浏览器）：
SMARTCAR_SOFTWARE_DEMO=1 bash scripts/start_terminal.sh
# 状态机与安全契约：
.venv-ros/bin/python -m pytest -q M5/M5-1/tests M5/M5-3/tests
# 隔离ROS插件后测模型流水线：
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv-model/bin/python -m pytest -q M6/M6-4/tests
```

各子目录README含独立复现命令。模型导出/量化用.venv-model；ROS/终端用.venv-ros；部署包自验用无训练框架的.venv-deploy。不要混用三套NumPy/ROS路径。Ubuntu依赖包括ros-humble-desktop、Gazebo classic、Nav2、slam_toolbox、ros2-control/ackermann、tf2_tools、PyQt5、nlohmann-json3-dev；项目构建用scripts/build_ros.sh。精确版本见THIRD_PARTY.md与准备日志。

Windows可通过SSH转发访问[监控终端](http://127.0.0.1:8080)。USB采集方法见hardware/k230/README.md。原始录音、室内照片、主程序备份留本地；Git包含源码、配置、非敏感统计与可公开训练图。大型rosbag/录像保留在Ubuntu和本地交付包，不把构建缓存或虚拟环境加入Git。

## 后续优先级

1. P0：Orin到货后开机联网，记录JetPack/驱动/ORT EP，先在干净运行时自验，再做板端CPU/GPU与支持的专用后端60秒基准。
2. P0：提供自有赛道权重、独立标注测试集，以及100～500张覆盖场景/光照的独立校准图；补逐类mAP、INT8精度下降和混合精度/QAT验收。
3. P1：在Orin实现并验证完整GPU预处理/推理/后处理、固定shape CUDA Graph及1000帧尾延迟，不能将模型体捕获当成整条链捕获。
4. P1：板端重测三线程与串行，按瓶颈优化≥1.6倍率及尾延迟；当前VM数据未达倍率，保留原始数据。
5. P1：若接实车/机械臂，补底盘硬件急停、真实导航/抓取和相机标定；当前软件Mock不替代实物。
