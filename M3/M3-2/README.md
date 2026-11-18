# M3-2：真实激光 SLAM

自建12×8m环形场景：中部8×4m岛状墙体，约2m宽走廊，长边巡场距离10m，底部1m窄门。窄门考验地图分辨率、墙边伪影以及后续膨胀层的可通行性。Gazebo激光为360线/10Hz，0.12～8m，噪声σ=0.01m。

```bash
source scripts/env.sh
.venv-ros/bin/python scripts/verify_mapping.py
.venv-ros/bin/python M3/M3-2/scripts/eval_map.py --map M3/M3-2/maps/map.yaml --out M3/M3-2/results/quality
```

使用 `slam_toolbox`，配置参数和理由在config/slam_params.yaml；0.05m栅格将1m门表示为约20格，车速直线0.25m/s、弯道0.13m/s，每次10Hz扫描约移动2.5cm。巡场使用SLAM的map→base TF跟随预定测绘路线，从未把Gazebo真值输入SLAM；真值只在M3-1做对照。路线绕岛一周后返回已扫描区域，`slam_route.csv`保留实际轨迹。

真实结果位于 `results/20261116_212209/`，ROS bag仍保留在Ubuntu相同目录的bag/。`maps/map.pgm`和map.yaml已由ROS标准map_saver保存，M3-3直接使用此图。

质量数据：北墙190个占据像素，拟合残差在浮点舍入范围内为0；这表示在0.05m栅格上共线，**不能宣称皮米级实际精度**。被重复观测的墙没有出现间隔超过2格的分离占据簇，墙厚最大1格；小于0.1m的鬼影不能由该判据排除。窄门实测19个自由格，宽0.95m。灰色岛体内部是雷达不可达的未知区域，不把它当成可导航空间。

图和数据见 results/quality/。回环是否建立额外图约束不能仅靠“地图墙直”推断；补充回放脚本 `scripts/verify_slam_replay.py` 保存实际序列化图和调试日志，回放输入仍是本次实测scan/odom/TF。

## AI参与与本人研究状态

本题由Codex协助代码/配置、实验验证及文档整理；已有实测证据见本页。本人逐行研究和独立复现程度尚未确认，待本人学习后更新。详细范围见[AI使用说明](../../AI_USAGE.md)，现场要求见[验收清单](../../docs/M1_M3_验收清单.md)。自动验证不替代本人理解或考官验收。

## 回环图约束与复现

实际保存的图位于 `results/replay_20261116_225310/`：265个节点、281条边，其中17条边连接ID相隔超过20的历史节点，时间间隔约131～141秒；原图、分析JSON和文本同时保留。校正后节点距离不是回环误差。

Git不含原始bag。可先运行 `scripts/verify_mapping.py` 重新采集，再运行 `scripts/verify_slam_replay.py --bag <新采集的bag目录>`；不传--bag时选择本机最新建图bag。需要检查图时：

```bash
cmake -S M3/M3-2/scripts -B tmp/posegraph_tool
cmake --build tmp/posegraph_tool
tmp/posegraph_tool/inspect_posegraph M3/M3-2/results/replay_20261116_225310/serialized_map.posegraph
```

构建依赖 `libboost-serialization-dev`、`libeigen3-dev`、`libtbb-dev`、`nlohmann-json3-dev` 和ROS slam_toolbox/karto SDK。读取工具需要完整的 `.posegraph` 文件名，不能只传给SLAM服务使用的文件名前缀。
