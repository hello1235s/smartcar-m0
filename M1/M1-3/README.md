# M1-3 时间同步与激光投影

此题使用培训仓库提供的合成 bag，和 K230 实拍数据明确分开；没有真实激光雷达时也能完整验证本题。

```bash
source scripts/env.sh
.venv-ros/bin/python scripts/verify_projection.py
# 手动复现，输出目录须自行指定：
python3 M1/M1-3/make_bag.py --frames 80 --out sample_bag --extrinsics extrinsics.yaml --laser-z 0.45 --camera-z 0.75 --fx 420
python3 M1/M1-3/projection_node.py --ros-args -p use_sim_time:=true -p extrinsics_file:=extrinsics.yaml -p output_dir:=projection_results -p slop:=0.02
ros2 bag play sample_bag --clock
```

静态树为 `map→odom→base_link`，再由 base_link 分叉至 laser_link、camera_link。离线样例没有车辆位姿变化，前两项为恒等变换；传感器 xyz/rpy 及相机内参全部读取外部 YAML。静态 TF 每秒重发，以便切换时钟导致 TF Buffer 清空后恢复。

投影先通过 TF2 查询 `camera_link←laser_link`，再把机体轴 `(X前,Y左,Z上)` 转成光学轴 `(-Y,-Z,X)`。只有正深度、有效量程且位于图像内的点会绘制；距离从近到远由红色过渡到蓝色。输出 `/projection/debug_image` 为 rgb8，沿用图像原时间戳。

同步采用真正的 `message_filters.ApproximateTimeSynchronizer`，队列 100；`sweep_sync.py` 读取实际 bag 时间顺序并调用同一同步器，不用“每帧找最近时间”替代算法。seed=7、80 个雷达帧的结果：

| slop | 配对数 | 时间差中位数 | P95 |
|---|---:|---:|---:|
|20 ms|80/80|9.430 ms|18.178 ms|
|40–150 ms|80/80|18.229 ms|34.497 ms|

本数据下 20 ms 已配满；增大 slop 没有增加数量，却使贪心匹配更早的图像。不能照抄题面示例中的配对趋势。节点保留契约默认 slop=50 ms，针对本样本推荐启动时改为 20 ms；现场换数据后重新扫描。

实际验收默认外参得到 39 对，非默认外参得到 72 对，均产出三张效果图。非默认运行切换时钟导致部分同步/TF 期间帧未输出，未把这些丢失帧算作成功。首帧投影纵坐标中位数从 249 px 变为 263 px，符合相机与激光高度差增大后点向图像下方移动。

`results/<运行时间>/` 保存外参、同步 CSV、原始生成/回放日志、TF PDF、效果图、真实应用窗口录像 `clock_switch_demo.avi` 和时钟观测 JSONL。录像仅录制当前 ROS 投影窗口，不采集整个桌面。`use_sim_time=false` 时节点时钟转为系统纪元时间，重新设 true 后回到 bag 时钟；图像/雷达消息头仍属于 bag 时间，时间域不可混用。

bag 可由脚本重生成，不把大体积 db3 当作代码提交。原 `make_bag.py` 仅复制自培训仓库，未修改生成算法。

## AI参与与本人研究状态

本题由Codex协助代码/配置、实验验证及文档整理；已有实测证据见本页。本人逐行研究和独立复现程度尚未确认，待本人学习后更新。详细范围见[AI使用说明](../../AI_USAGE.md)，现场要求见[验收清单](../../docs/M1_M3_验收清单.md)。自动验证不替代本人理解或考官验收。

## 本轮完整复测

本轮已重新执行题面检查，任务内容、逐项结果和原始总报告见[完整验收](../ACCEPTANCE.md)。历史测量保留原日期，不冒充本轮成绩。
