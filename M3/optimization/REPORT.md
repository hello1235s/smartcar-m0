# M3优化实测总报告

本轮在Ubuntu 22.04、ROS2 Humble、Gazebo Classic 11、VMware 6 vCPU中实际运行。结果对应当前后轴TF与M3-2新建地图；历史2026-11-16结果单独保留。源码、逐次参数、运行库、地图哈希和完整成败记录可独立核对。不是实车验收，也不把有限样本称为“完美”。

## 结果

- 方形反馈闭环10次：后轴真值位置误差0.018285±0.005359m，朝向1.637736±0.191802°，±为样本标准差。
- 当前SLAM图：0.05m栅格、0.95m地图窄门、268节点/284边/17条历史非邻接约束。北墙共线只反映栅格尺度，不是零误差声明。
- 默认静态导航：严格10/10，成功平均57.350仿真秒，最大真值位置/朝向误差0.0991m/0.0697rad。
- 标称动态B_tuned：严格10/10；完整参数对照如下。

|配置|严格成功|成功平均耗时|实际额外路径|指令转向TV|
|---|---:|---:|---:|---:|
|A|10/10|49.350 s|0.148 m|0.990 rad/m|
|B|9/10|36.556 s|0.125 m|1.410 rad/m|
|B_tuned|10/10|47.450 s|-0.230 m|0.871 rad/m|

依据与限制见[完整CSV](report/all_attempts.csv)、[分组统计与置信区间](report/summary.json)、[口径定义](report/method.json)、[四指标图](report/metrics.png)、[全部轨迹图](report/trajectories.png)、[真实代价地图](report/costmaps.png)和[控制曲线](report/commands.png)。每组10次，10/10的Wilson 95%区间下限仍约72.2%，不是任意环境成功保证。

## 实现变化与因果边界

1. 修正参考点：后轴中点与控制器积分点一致，base_link固定向前0.14m。物理尺寸不变，规划footprint同步平移，SLAM实际重建。
2. 定时巡航改为odom反馈、加减速、单调路径进度和终点联合判定；真值仅记录。新速度较慢，因此不能把新旧闭合改善全算作反馈收益。新后轴误差统一到车体中心后约0.02156±0.00468m，历史0.2843±0.0408m，两者采用同一物理参考点才可对照。
3. 同速参考点/控制方式消融的单次探索全部保留：原参考定时约0.1314m、后轴参考定时约0.1415m、原参考反馈约0.0200m、后轴参考反馈约0.0185m。单次不作为显著性检验，只说明主要收益与反馈相关，不能把它归功于移动坐标原点。
4. Nav2使用SmacHybrid/Reeds-Shepp、AckermannRPP、有界倒车平滑链，关闭原地旋转。控制器在碰撞预测之前限制曲率，并用0.45m虚拟末端参考引导朝向；请求目标不移动，近端按路径终点距离减速。当前默认xy/yaw容差0.02m/0.10rad，外部真值验收仍≤0.15m/0.20rad；A/B历史基线保持0.05m内部停车。收紧余量用于容纳已观测的栅格终点偏移、跟踪余量与定位误差，不靠放宽验收过关。
5. 默认0.08m规划padding、0.45m软膨胀，给定位、栅格和跟踪误差留余量。早期内岛拐角包络越界失败保留，规划余量不用于缩小独立评价车身。
6. 修复Humble目标检查路径的TF失败假成功：无效目标四元数被新增插件拒绝。原错误曾在仅行驶约0.24m时返回Action成功，被独立真值门槛拦截。10项Python测试与4项C++回归（位姿有效性、车辆曲率/末端速度约束、标准/扩展插件加载、TF2回调锁顺序）通过。
7. Fast DDS候选静态8/10，换CycloneDDS后动态仍9/10。进一步发现系统TF2 0.25.23具有上游确认的回调锁反转，与所见TF缓存停滞现象一致：本机两线程回归旧库稳定超时、官方0.25.24核心库通过，见[锁顺序回归](report/tf2_lock_regression.json)和[官方修复PR990](https://github.com/ros2/geometry2/pull/990)。仅在M3进程内加载修复，不修改M1系统环境；各次保存控制器、规划器和AMCL实际加载的TF2库路径。最终对照在修复后全部重采，旧失败完整保留，不把DDS切换独立宣称为根因修复。原故障未取得GDB线程栈，对原现场机制的判断是结合现象、官方修复与本地回归的推断。

地图序列化还通过原生Nav2回验：保留原SLAM像素，仅修正free_thresh 0.25→0.196，使12820个灰色未知格不再错误变成自由格。原生map_server加载后1600占据/12820未知/24784自由与原PGM完全一致。当前正式统计均使用修正后的同一PGM与YAML哈希，修正前候选单列保留。

## 新位置、新目标与边界

|独立场景|严格到达次数|全部尝试最小几何间距(m)|
|---|---:|---:|
|heldout_obstacle_east|2/2|0.2549|
|heldout_obstacle_gate_exit|2/2|0.1572|
|heldout_goal_northeast|2/2|0.2023|
|heldout_goal_far_northwest|2/2|0.1567|
|boundary_blocked_goal|0/1|0.1143|
|boundary_close_front|0/1|0.1314|

目标被0.8m箱体占据的场景预期不可达；应检查Action失败/超时、最终速度和几何间距，不把“正确拒绝”混进到达成功率。独立场景的原始CSV、具体坐标/目标/尺寸和失败原因见`extended_report/`及对应实验快照。这些固定额外位置仅提供有限覆盖，不是盲测或随机采样的泛化保证；未测高速移动障碍或真实道路，不扩展结论。

## 指标与证据

严格成功同时要求Action成功、独立世界真值终点合格、有效路径超过5m、激光/真值样本充分、保守轮组包络没有与已知方盒重叠，动态场景还要求实体注入成功。碰撞项是基于采样世界位姿和已知几何的独立包络检查，不是Gazebo接触传感器认证。

主路径长度为世界真值积分，额外路径减同一配置成功无障碍参考均值；无成功参考时为N/A。耗时是接受目标到Action结束的仿真时间，不包含停车等待。转向TV来自底盘桥reference的`atan(0.28*omega/v)`，除以真值距离，不冒充转向关节实测。

保存实际/plan、odom、world_truth、map估计、指令、几何间距、行为树事件和全局/局部OccupancyGrid数组。周期性注入后下一条plan与FollowPath失败后有效新plan分别记录；没有失败或没有后续有效plan时保留空值。全部失败在成功率分母，不只挑成功截图。

## 复现

```bash
bash scripts/build_ros.sh
bash scripts/install_m3_runtime.sh
source scripts/env.sh
.venv-ros/bin/python -m unittest discover -s M3/tests -v
ctest --test-dir build_ros/smartcar_nav_checks --output-on-failure
bash scripts/run_m3_demo.sh square
bash scripts/run_m3_demo.sh static
bash scripts/run_m3_demo.sh dynamic
```

Gazebo实验依次运行，自动入口会锁定同机M3实验并创建新目录。完整批次：`run_qualification.py --suite main`和`--suite extended`；重新建图用`verify_mapping.py`，只有通过才晋级，已有正式结果的地图快照不被改写。大型bag/完整运行日志在Ubuntu和本地交付包，Git保留关键原始CSV/JSON与图。答辩准备和PDF只保留本地。

## 来源

题面与原始车：[Blake-John/22SmartCar](https://github.com/Blake-John/22SmartCar)。后轴里程计依据[Humble steering_odometry.cpp](https://github.com/ros-controls/ros2_controllers/blob/humble/steering_controllers_library/src/steering_odometry.cpp)。目标TF失败链路核对[Humble ControllerServer](https://github.com/ros-navigation/navigation2/blob/humble/nav2_controller/src/controller_server.cpp)及[tf_help.cpp](https://github.com/ros-navigation/navigation2/blob/humble/nav2_dwb_controller/nav_2d_utils/src/tf_help.cpp)。UDP配置核对[Fast DDS 2.6环境变量文档](https://fast-dds.docs.eprosima.com/en/2.6.x/fastdds/env_vars/env_vars.html)。AI参与范围、本人研究状态和软件来源另见根目录说明。

## 同速十次重复消融

定时与odom反馈均用后轴参考、0.28/0.18m/s和同一2m圆角轨迹，各10次。定时真值闭合 0.079965±0.027714m，反馈 0.018285±0.005359m，均为均值±样本标准差；本样本位置均值降低约77.1%。两批噪声时序不同，不冒充成对显著性检验。时间代价与角度见square_matched_speed.json/图。

## 原终点超差的修正与完整新验证

旧版本d02cdf7的9/10及15.1523cm失败原样保留，来源为`M3/optimization/results/20261121_033452_tf2q_formal_dynamic_B_tuned/run_02`。该次请求目标到栅格路径终点约2.915cm，估计停车点到路径终点约4.745cm，估计位置与世界真值约8.715cm；这是误差向量分解，不是三条标量简单相加，也不是普遍误差上界。

只将内部XY停车余量0.05→0.02m，减少3cm跟踪余量。地图、AMCL、车辆、请求目标、C++控制内核以及外部0.15m/0.20rad门槛均未改变；真值不反馈控制。先导种子201与正式新十次分开保存，不把先导计入成绩。

固定种子200～209的新动态完整10/10，最大真实位置误差0.050151m、最大朝向误差0.044465rad；新增静态10/10，最大位置0.099129m。新目录与冻结版本见`M3/optimization/results/20261121_152430_terminal_refinement/validation.json`。A/B和早期诊断保留原样，未冒称重新采集；图表当前B_tuned使用本次20条新记录及同配置静态参考。上一版报告完整保存在该目录previous_release_report中。

内部停车容差属于这次明确调优的变量：A/B及旧中间组仍0.05m，最终B_tuned为0.02m；各组外部物理验收一致。新十次全过只说明本次条件，不证明任意噪声和任意现场100%。

相机额外0.01m前界复核已按当前62条对照/扩展记录重算，最小间距0.025651m、重叠0；不重写原体轮评分，也不等同连续接触认证。
