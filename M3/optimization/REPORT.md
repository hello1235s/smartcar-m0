# M3当前优化与现场验证报告

2026-11-22，Ubuntu22.04 / ROS2 Humble / Gazebo Classic11 / VMware6vCPU。冻结控制源码1b2e64ac8e39e7704654daf251d5cdf605532210；46次当前主对照/无障碍参考全部新采集，另有当前版5次新场景。旧版52条与6条中间诊断保留在独立历史入口，不混入当前控制内核。

## 当前主对照

|方案|成功/10|成功耗时s|额外路径m|指令转向TV rad/m|
|---|---:|---:|---:|---:|
|A|10/10|48.8300|0.1356|0.8745|
|B|8/10|37.7250|0.4499|1.4670|
|B_tuned|10/10|44.2900|0.1293|0.7610|


默认静态B_tuned严格10/10，成功耗时43.7400仿真秒，最大真值位置0.0697m、朝向0.0562rad。A/B各有3次同内核无障碍参考，B_tuned有10次；全部46次见[CSV](report/all_attempts.csv)、[统计](report/summary.json)、[四指标](report/metrics.png)、[动态30次全部轨迹](report/trajectories.png)。

## 本轮实际修复

原临时RViz目标第一次成功，第二次150秒超时；虽然真值已接近1.46cm，Action没有成功，仍保留为失败。末端全局路径出现厘米级倒车再前进折返，车辆反复换向，最小估计路径终点误差2.676cm，未进入2cm目标范围。原始[失败结果](results/20261122_124502_showcase_rviz_goal/run_02/result.json)与[路径](results/20261122_124502_showcase_rviz_goal/run_02/plans.json)保留。

修复仅在距实际路径目标20cm内、朝向已满足目标检查器、横向误差小于其XY容差75%时，沿真实目标朝向构造局部末端参考，避免追踪微型折返。未更换目标、不喂真值、不改变碰撞检查或物理尺寸。内部B_tuned仍2cm/0.10rad，A/B仍5cm/0.10rad，外部独立验收仍15cm/0.20rad。先导、正式批次、现场GUI分别保存，不用先导替代十次分母。

## 最新展示入口与证据

- 原PGM经原生map_server加载，1600占据/12820未知/24784自由不变；RViz原生渲染内部截图可见原地图。[工程验收索引](../../docs/showcase_acceptance.md)。
- 真实SLAM巡场录制154次地图更新、471次TF采样与487帧视频；新图通过检查但不晋级，正式导航PGM/YAML不变。
- RViz原生工具真实鼠标拖选新地图目标，修复后重新跑两次，严格2/2，最大真值位置误差0.0646m。代理选点模拟临时考题，不冒充真实考官随机考核。
- 新障碍世界(9.2,1.3)当前版2/2；实体在首次/odom运动超过0.02之后3秒生成，激光观测更新代价地图。当前正式三组也使用这个运动起点口径；旧批次从目标接受计时，另存历史。
- 目标世界(11,5)被0.8m箱覆盖：90秒试验器看门狗取消并停车，未收到Action终态，原始Action状态None，结束原因simulation_timeout，末速度0.0001m/s，最小几何间距0.0996m，重叠采样0。预期不可达，不能计为到达成功；Action失败与试验器超时要分开。

## 四指标与取舍

成功率使用全部尝试；耗时仅平均严格成功样本，从接受目标到Action结束，展示停留不计时；额外路径为实际世界真值积分减同配置成功无障碍参考均值，负值保留并解释路径与定位波动；平滑度为底盘reference指令转向角总变化/真实里程，非轮胎关节磨损实测。10/10的Wilson95%下限约72.2%，有限样本不能保证任意现场成功。

## 失败、重规划与历史

[失败逐例](report/failure_cases.md)包含当前全部未到达数据；[完整候选审计](report/experiment_audit.json)包含旧失败、被拒方案和本次修复前超时。FollowPath错误到后续有效plan的墙钟配对见[主对照](report/replanning_detail.json)与[新场景](extended_report/replanning_detail.json)；无事件留空，不把周期1Hz更新冒称故障恢复。主对照出现错误6次，新场景1次。有新路径不代表最后一定到达。

旧版参数消融仍可从[历史报告快照](../../evidence/M3-showcase-qualification/20261122_125957/previous_release_report)回看，包括速度、前视、预测时域与内部停车余量。它们不与本次新内核样本拼成单因素因果链。本次三组参数比较共享新的同一内核和相同地图、目标、尺寸与运动起点计时。

## 其他已验证基础与限制

方形巡航十次、同速定时/反馈对照和正式SLAM地图仍使用原合格来源；本轮未改该控制路径或地图。TF2官方项目级修复与CycloneDDS保持，真实controller/planner/AMCL加载路径逐次通过核验。几何安全为已知方盒与采样位姿包络，不是实车或连续接触认证；另按相机前突1cm重算[前包络审计](report/camera_margin_audit.json)，本次状态为REVIEW。激进B包含独立保守包络重叠，因此该比较方案不能宣称安全通过；默认采用B_tuned没有前包络重叠。审计的REVIEW与原返回码保留，不改成全部安全PASS。

## 复现

```bash
source scripts/env.sh
bash scripts/run_m3_demo.sh square
.venv-ros/bin/python scripts/run_m3_map_demo.py
bash scripts/run_m3_demo.sh mapping --no-promote --viewer
bash scripts/run_m3_demo.sh target
bash scripts/run_m3_demo.sh dynamic
# 当前完整三组与匹配参考（耗时较长，不与现场演示同时起）
.venv-ros/bin/python M3/M3-4/scripts/run_benchmark.py --runs 10
```
