# M1-1 三节点与动态参数

从仓库根目录执行：

```bash
bash scripts/build_ros.sh
source scripts/env.sh
ros2 run smartcar_training node_a_sensor
# 另外两个终端同样 source scripts/env.sh，然后分别运行：
ros2 run smartcar_training node_b_filter
ros2 run smartcar_training node_c_alarm
ros2 param set /node_b_filter alpha 0.9
ros2 service call /trigger_alarm sensor_interfaces/srv/TriggerAlarm '{distance: 0.1}'
```

`sensor_interfaces/msg/SensorData` 严格使用题目规定的四个字段及顺序。题面没有给出服务字段，本文明确约定 `TriggerAlarm` 请求为 `float32 distance`，响应为 `bool success / string message`。节点 B 同时承载报警服务，保持三个常驻节点；服务也可通过 `alarm_service_enabled` 参数启停。

话题与服务均使用相对名：无命名空间时为 `/sensor_data`、`/processed_distance`、`/trigger_alarm`。传感器每 40 帧发送一帧无效状态，滤波器跳过并告警。首个有效值用于初始化滤波；后续按题目的一阶公式计算。`alpha` 必须为有限 double，范围 `(0,1]`，非法更新会被拒绝。

报警客户端使用异步 Future 与独立轮询计时器，按单调时钟计算 1 秒超时；服务不存在也会超时告警，不阻塞 executor。每次报警限制重入，避免请求堆积。

自动验收：`.venv-ros/bin/python scripts/verify_m1_chain.py`。已实测传感器 10.010 Hz、有效滤波输出 9.842 Hz；参数修改与非法值拒绝通过；实际杀掉节点 B 后，节点 C 出现 `[WARN] 报警服务超时`。原始记录在 `evidence/M1-chain/`，保留失败尝试，最新通过结果为 `latest.json`。

故障排查：接口包需在 package.xml 中声明 `ament_cmake` build_type。曾因缺少该声明导致构建缓存类型不一致、目录与符号链接冲突；现使用独立 `build_ros/install_ros/log_ros` 目录，保留原缓存供追溯。

## AI参与与本人研究状态

本题由Codex协助代码/配置、实验验证及文档整理；已有实测证据见本页。本人逐行研究和独立复现程度尚未确认，待本人学习后更新。详细范围见[AI使用说明](../../AI_USAGE.md)，现场要求见[验收清单](../../docs/M1_M3_验收清单.md)。自动验证不替代本人理解或考官验收。
