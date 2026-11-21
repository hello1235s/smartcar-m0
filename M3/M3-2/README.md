# M3-2：真实激光SLAM、回环与地图晋级检查

自建12×8m环形场景，中部8×4m岛状墙体、约2m走廊、底部1m物理窄门。激光360线/10Hz、0.12～8m、噪声σ=0.01m。`slam_toolbox`使用scan、轮式odom和传感器TF，巡场跟踪SLAM定位，不使用Gazebo真值控制或建图。

本轮修正后轴TF后重新实际巡场建图。当前导航图来自`M3/M3-2/results/20261121_001551_qualified_mapping`，SHA256为`43f1e9f41b6957d041239f81345b6dfe9ccc6b51ff1aa233f700f63960613dda`；`maps/map_manifest.json`记录验收与来源。地图0.05m分辨率，窄门19个自由格，即0.95m。北墙190个占据点在该栅格上共线、最大观测墙厚1格，没有发现间隔超过2格的分离占据簇。这只能说明栅格尺度下没有检出的重影，不能证明零漂移或皮米级精度。未知区域不允许规划通行。

另做了真实Nav2加载回验：原保存阈值0.25会把灰205未知格读成自由格，修正free_thresh为0.196，PGM像素完全不变。原生map_server返回1600占据、12820未知、24784自由格，与PGM逐类计数完全相同；检查报告与修正前失败均保留，当前map_manifest记录YAML哈希。此后导航统计全部重新采集，不能混入修正前成绩。

分辨率0.05m使0.45m车长约9格、地图窄门约19格，兼顾厘米级激光噪声、通道几何和虚拟机开销。自定难点为1m物理窄门：预期定位和栅格误差会压缩通行余量，实测地图剩0.95m，按0.26m车/轮包络加两侧0.08m余量后仍有约0.53m横向总余量；这只是宽度核算，实际转向可达性仍由轨迹实测。未把仿真器没有模拟的玻璃反射等现象写成已验证。

SLAM仍运行时调用真实序列化服务，得到268节点、284边的图，其中17条连接历史时段的非邻接约束。原`.posegraph`/`.data`、分析JSON、实际路线CSV和地图质量图同目录保留。图中校正节点间距离不是回环误差。旧265节点/281边的历史图仍保留在原results目录。

```bash
source scripts/env.sh
# 单命令巡场、录bag、序列化图、保存地图、质量检查
.venv-ros/bin/python scripts/verify_mapping.py
# 只验证新地图，不替换正在使用的导航图
.venv-ros/bin/python scripts/verify_mapping.py --no-promote
```

只有巡场完整、墙体/窄门检查通过且存在历史图约束才晋级到`maps/`，失败图和日志保留。导航正式对照全部使用同一个固定地图哈希，不能在对照中间换图。原始bag体积较大，不放Git；在Ubuntu原实验目录和本地完整交付包保留，可用上述命令重新采集。

独立检查实际图：

```bash
cmake -S M3/M3-2/scripts -B tmp/posegraph_tool
cmake --build tmp/posegraph_tool
# 传完整.posegraph文件名，不能只传服务使用的前缀
tmp/posegraph_tool/inspect_posegraph <path/to/serialized_map.posegraph>
```

## 来源、AI参与与现场边界

使用题面车辆与历史文件，物理尺寸未缩小。Codex参与实现、调参、真实进程验证和文档整理；本人独立复现与逐行理解程度需本人确认。见[AI使用说明](../../AI_USAGE.md)和[验收清单](../../docs/M1_M3_验收清单.md)。全部M3结果为Gazebo仿真，不宣称实车道路性能；旧结果和失败样本保留，不代表任意目标都能成功。
