# M3-3：阿克曼定位导航与严格终点验收

使用本轮M3-2实际SLAM地图，AMCL根据地图和激光发布`map→odom`，轮式控制器发布`odom→base_footprint`。已知固定出生点对应地图(0,0,0)作为初始定位，Gazebo真值不进入TF、AMCL或控制，仅用于独立验收。

正式固定种子组完成10/10次严格通过，成功平均57.350仿真秒；真值位置误差均值0.049m、最大0.099m，朝向误差最大0.070rad。每次目标路径超过5m且包含转弯，完整成败行见[本轮CSV](../optimization/report/all_attempts.csv)。历史2/3和本轮口径不同，旧结果保留，不能直接当成同条件百分点收益。

## 选型与参数

全局`SmacPlannerHybrid/REEDS_SHEPP`，局部为基于Humble RPP扩展的`smartcar_nav_checks::AckermannRPP`；最小规划半径0.65m，控制器在碰撞预测前把曲率限制到≥0.60m转弯半径，底盘桥再兜底。规划器、RPP和速度平滑器同时支持有界倒车，最大倒车速度0.20m/s；关闭原地旋转。相比前向Dubins，Reeds-Shepp可提供符合非完整约束的末端修正路径。MPPI也是可选方案，但本次没有把未做公平重复实测的方案宣称更优。

末端跟踪使用0.45m虚拟朝向参考，真实Nav2目标不变；0.60m内按0.7×目标距离减速（不强行提高更低的安全速度）。预测采用实际受限车辆弧线，终点附近不要求驶过真实目标。`controller_commands.csv`记录底盘限幅前的原始请求，用于量化控制器是否请求了不可实现的急转弯。

默认巡航0.32m/s，速度相关前视0.30～0.65m、前视时间1.2s；碰撞预测2.0s；当前默认xy容差0.02m、yaw容差0.10rad。独立验收更关注最终物理位置：≤0.15m且≤0.20rad、路径≥5m、保守包络无重叠、激光/真值样本充分。代价地图footprint另加0.08m规划余量，膨胀0.45m是软代价场；0.95m门比0.26+2×0.08=0.42m包络宽，膨胀半径不是一刀切禁行带。完整默认值→新值→理由见`config/changes.yaml`与带注释的`nav2_params.yaml`。

## 修复过的真实失败

1. 旧配置行为树绝对路径指向其他目录：launch现在根据当前checkout解析，原参数文件不被运行过程改写。
2. 前向导航进入位置容差但朝向差约14°，继续绕行后中止：完整倒车规划/跟踪链解决候选问题，仍以重复真值验收为准。
3. 反复启动曾出现TF缓存停滞：Fast DDS候选静态8/10，更换CycloneDDS后动态仍9/10，未误称更换DDS已彻底修复。发现系统TF2 0.25.23具有上游已修复的回调锁反转；本机两线程回归旧库超时、官方0.25.24库通过，现仅在项目内加载TF2核心修复。C++节点实际加载路径逐次保存。M1系统环境不变，M3方形/建图保持原DDS并加载修复，Nav2使用CycloneDDS本机单播。固定地图目标按最新TF转换；整套最终对照在修复后重采，旧失败不混算。见`../optimization/report/tf2_lock_regression.json`与官方geometry2修复PR990。
4. Humble目标TF转换失败时曾出现车只走0.24m就Action成功。新增C++`ValidPoseGoalChecker`拒绝零/非有限/非单位四元数，始终同时检查xy和yaw。插件与上游接口兼容，独立回归测试覆盖实际失败形态；即使Action成功，外部真值门槛仍会拦截假成功。
5. 内岛拐角曾擦入保守包络：增加规划余量和软代价场。后续标准RPP候选即使静态9/10，仍有末端绕行碰外墙；因此没有采用，新增阿克曼曲率预测与末端朝向引导后重新完整验收，失败CSV全部保留。

```bash
bash scripts/build_ros.sh
bash scripts/install_m3_runtime.sh
source scripts/m3_nav_env.sh
# 一条launch同时起Gazebo、地图、AMCL、Nav2
ros2 launch ./M3/M3-3/bringup.launch.py
# 与上一条二选一：自启并清理仿真，实际发送任意地图目标
bash scripts/run_m3_demo.sh static --goal 10,4,1.5707963268
# 批量严格验收，不开图形界面
.venv-ros/bin/python scripts/verify_navigation.py --runs 3
```

同一时刻只运行一个Gazebo实验。演示脚本会创建新结果目录并清理自身进程；不要后台叠加上一条launch。代价地图原始OccupancyGrid数组、全局路径、odom、真值、控制指令、行为树事件均有记录；图见[优化报告](../optimization/report/)。未见目标的测试、失败边界和统计置信区间一起报告，10/10也不代表所有目标都可达。

## 来源、AI参与与现场边界

使用题面车辆与历史文件，物理尺寸未缩小。Codex参与实现、调参、真实进程验证和文档整理；本人独立复现与逐行理解程度需本人确认。见[AI使用说明](../../AI_USAGE.md)和[验收清单](../../docs/M1_M3_验收清单.md)。全部M3结果为Gazebo仿真，不宣称实车道路性能；旧结果和失败样本保留，不代表任意目标都能成功。
