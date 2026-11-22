# 最新M1/M3展示指南：工程补齐验收

2026-11-22。依据教师仓库[dbfd7cf](https://github.com/Blake-John/22SmartCar/tree/dbfd7cf6cbfaec4380e7f5a24654e38c24292732)的最新展示指南。本人仍须独立操作和回答问题，以下表示程序和工程证据已执行验证。

|范围|实际完成|原始证据|
|---|---|---|
|M1全四题|接口/数值/隔离/两外参/语义与60秒性能通过|[打开证据](../evidence/M1-M3-showcase/20261122_122455/full_m1/results.json)|
|单命令双组|同一launch一次启动六节点；两组参数和话题隔离|[打开证据](../evidence/M1-dual-launch/20261122_122944/results.json)|
|逐点距离|6张图全部像素和点距离与原bag独立核对|[打开证据](../M1/M1-3/results/20261122_122516/pixel_oracle.json)|
|原PGM原生RViz|map_server返回原网格；官方RViz内部渲染截图可见地图|[打开证据](../M3/M3-2/results/20261122_124340_native_rviz_map/verification.json)|
|原生RViz实际图|外部黑色读回已拒绝并留记录|[打开证据](../M3/M3-2/results/20261122_124340_native_rviz_map/native_rviz_render.png)|
|真实SLAM操作|154次地图更新/471个TF位姿/487帧真实应用窗口AVI，新图未替换正式图|[打开证据](../M3/M3-2/results/20261122_123240_showcase_recording/actual_operation/actual_slam_operation.avi)|
|本轮46次主验证|同一冻结控制内核；B_tuned静态10次、A/B静态各3次，动态三组各10次|[打开证据](../evidence/M3-showcase-qualification/20261122_125957/main_manifest.json)|
|新RViz目标|实际G工具鼠标拖选；两次均严格通过，实际目标和输入单独保存|[打开证据](../M3/optimization/results/20261122_135046_showcase_fixed_rviz_goal/runs.json)|
|新障碍两次|世界(9.2,1.3)，运动后3秒插入，2/2通过|[打开证据](../M3/optimization/results/20261122_134650_showcase_fixed_new_obstacle_twice/runs.json)|
|目标占据边界|当前2cm版本，预期不可达；Action状态与停车按实测记录|[打开证据](../M3/optimization/results/20261122_134854_showcase_fixed_blocked_goal_boundary/runs.json)|
|视频解码检查|所有选定视频首中尾可解码且非黑屏|[打开证据](../evidence/M1-M3-showcase/20261122_122455/video_integrity.json)|
|本轮总索引|所有判断、来源与限制可追溯|[打开证据](../evidence/M1-M3-showcase/20261122_122455/validation.json)|


当前控制冻结于`1b2e64ac8e39e7704654daf251d5cdf605532210`，本次末端微折返修复后重新采46次主对照，另5次当前场景。M1功能验收在本次进行，后续改动为M3控制和原生RViz展示组件，M1数据算法未再变化。

M1的60秒输入31.999Hz、输出32.000Hz、控制21.000Hz、P95 12.410ms。输入为发布者自报；输出/控制与延迟由接收端实测。当前M3动态A/B/B_tuned严格成功分别为10/10、8/10、10/10。

## 本轮修复与历史

修复前的真实RViz两次有一次150秒超时，仍保留[原结果](../M3/optimization/results/20261122_124502_showcase_rviz_goal/runs.json)。微型末端折返会让车辆已接近终点却反复换向；修复只在已对齐、足够近且横向误差很小时沿真实目标朝向构造局部参考。目标、地图、定位、真值评价与碰撞检查没有替换。内部2cm/0.10rad和外部15cm/0.20rad未放宽。

旧52条主/诊断与旧接受目标+3秒口径单独存档；当前46条是相同新内核和运动起点+3秒。旧中间速度/前视诊断不混进本轮统计，失败不重抽。[当前总报告](../M3/optimization/REPORT.md)提供四指标、失败逐例、重规划配对和源版本。

原生RViz使用官方VisualizationFrame、Map插件与渲染窗口内部截图；不重画地图。SLAM和导航2D查看器的视频是实际ROS应用窗口，不能说成Gazebo3D录像。临时新点由代理选定以模拟现场改题，不等于真实考官随机考核。10/10是有限样本；无法保证任何环境、任意目标都成功。

[现场命令](现场展示入口.md)；[M1逐题](../M1/ACCEPTANCE.md)；[M3逐题](../M3/optimization/acceptance_matrix.md)。个人答辩手册与PDF单独本地保存，不进Git。
