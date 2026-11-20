"""Update current M3 explanations from measured JSON; retain historical evidence."""
import json
from pathlib import Path
import statistics
ROOT=Path(__file__).resolve().parents[2]


def write(path,text): (ROOT/path).write_text(text.strip()+'\n',encoding='utf-8')
def f(value,digits=3): return 'N/A' if value is None else f'{value:.{digits}f}'


def main():
    report=ROOT/'M3/optimization/report'
    summaries=json.loads((report/'summary.json').read_text()); groups={s['group']:s for s in summaries}
    static=groups['formal_static_B_tuned']; dynamic=[groups['formal_dynamic_'+p] for p in ['A','B','B_tuned']]
    assert static['attempts']==10 and all(s['attempts']==10 for s in dynamic)
    square=next((ROOT/'M3/optimization/results').glob('*qualified_feedback_rear'))
    runs=json.loads((square/'logs/runs.json').read_text())
    mean=lambda key:statistics.mean(r[key] for r in runs)
    sd=lambda key:statistics.stdev(r[key] for r in runs)
    map_info=json.loads((ROOT/'M3/M3-2/maps/map_manifest.json').read_text())
    common='''
## 来源、AI参与与现场边界

使用题面车辆与历史文件，物理尺寸未缩小。Codex参与实现、调参、真实进程验证和文档整理；本人独立复现与逐行理解程度需本人确认。见[AI使用说明](../../AI_USAGE.md)和[验收清单](../../docs/M1_M3_验收清单.md)。全部M3结果为Gazebo仿真，不宣称实车道路性能；旧结果和失败样本保留，不代表任意目标都能成功。
'''
    write('M3/M3-1/README.md',f'''# M3-1：阿克曼坐标系与里程计反馈闭环

从题面原车建立`smart_car_description`：车体0.45×0.22m、轴距0.28m、轮距0.18m、轮半径0.05m和转向限位±0.5236rad不变。保留`*.original.*`。Humble控制器轮序按RIGHT/LEFT适配，公共`/cmd_vel`经原底盘桥转换为控制器带时间戳的reference。

## 本轮改进与十次真值结果

原来按时间切换直行和转弯；现在`ForwardTracker`仅用`/odom`反馈控制2m外包络圆角正方形，圆角半径0.65m、直段0.7m。加入加减速、终点延伸和位置/朝向同时判定，防止刚出发因起终点重合而提前结束。直行0.28m/s、转弯0.18m/s，实际每圈{mean('sim_seconds'):.2f}秒。Gazebo真值只记录和评价，不输入控制，也不拿它修正odom。

|10次结果|均值|样本标准差|
|---|---:|---:|
|后轴真值闭合位置(m)|{mean('truth_position_error_m'):.6f}|{sd('truth_position_error_m'):.6f}|
|真值闭合朝向(°)|{mean('truth_angle_error_deg'):.6f}|{sd('truth_angle_error_deg'):.6f}|
|odom闭合位置(m)|{mean('odom_position_error_m'):.6f}|{sd('odom_position_error_m'):.6f}|
|odom闭合朝向(°)|{mean('odom_angle_error_deg'):.6f}|{sd('odom_angle_error_deg'):.6f}|

原始CSV与每圈控制记录：[本轮十次](../{square.relative_to(ROOT/'M3').as_posix()})。旧的2026-11-16十次数据仍在`results/20261116_210401/`，旧真值位置0.2843±0.0408m、角度15.80±2.37°。新旧速度和参考点不同，因此不能把全部改善归因于单一参数。统一到车体中心后，本轮闭合位置约0.02156±0.00468m。低速定时控制与反馈控制的消融样本及完整来源见[优化报告](../optimization/REPORT.md)。改善有时间代价，不冒称轮式里程计本身已达到厘米级定位精度。

## 后轴参考点与TF

控制器积分点是后轴中点；`base_footprint`与其对齐。`base_footprint→base_link`固定变换为`(+0.14,0,+0.05)m`，传感器与车体的关系不变。规划footprint采用后轴坐标下的0.45×0.26m保守车体/轮组包络，另在代价地图增加规划余量。重建SLAM后才用于导航。`map→odom`在本题不存在，在M3-2由SLAM发布，在M3-3/4由AMCL发布。TF图见`results/tf_tree_annotated.png`。

中心最小转弯半径约`0.28/tan(0.5236)+0.18/2=0.575m`；底盘桥保守限制0.60m，参考轨迹0.65m。阿克曼不能原地转向，但可以沿可行曲线前进或倒车。

```bash
bash scripts/build_ros.sh
source scripts/env.sh
# 十次完整测试与统计，独立创建输出目录
.venv-ros/bin/python scripts/verify_square.py
# 现场一圈并显示Gazebo
bash scripts/run_m3_demo.sh square
# 保留定时模式用于消融；不覆盖已保存成绩
.venv-ros/bin/python M3/optimization/run_square_trial.py \\
  --mode timed --laps 10 --label matched_timed_rear
```
{common}''')
    write('M3/M3-2/README.md',f'''# M3-2：真实激光SLAM、回环与地图晋级检查

自建12×8m环形场景，中部8×4m岛状墙体、约2m走廊、底部1m物理窄门。激光360线/10Hz、0.12～8m、噪声σ=0.01m。`slam_toolbox`使用scan、轮式odom和传感器TF，巡场跟踪SLAM定位，不使用Gazebo真值控制或建图。

本轮修正后轴TF后重新实际巡场建图。当前导航图来自`{map_info['source_trial']}`，SHA256为`{map_info['map_sha256']}`；`maps/map_manifest.json`记录验收与来源。地图0.05m分辨率，窄门19个自由格，即0.95m。北墙{map_info['quality']['wall_points']}个占据点在该栅格上共线、最大观测墙厚1格，没有发现间隔超过2格的分离占据簇。这只能说明栅格尺度下没有检出的重影，不能证明零漂移或皮米级精度。未知区域不允许规划通行。

另做了真实Nav2加载回验：原保存阈值0.25会把灰205未知格读成自由格，修正free_thresh为0.196，PGM像素完全不变。原生map_server返回1600占据、12820未知、24784自由格，与PGM逐类计数完全相同；检查报告与修正前失败均保留，当前map_manifest记录YAML哈希。此后导航统计全部重新采集，不能混入修正前成绩。

SLAM仍运行时调用真实序列化服务，得到{map_info['graph']['vertices']}节点、{map_info['graph']['edges']}边的图，其中{map_info['graph']['historic_constraints']}条连接历史时段的非邻接约束。原`.posegraph`/`.data`、分析JSON、实际路线CSV和地图质量图同目录保留。图中校正节点间距离不是回环误差。旧265节点/281边的历史图仍保留在原results目录。

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
{common}''')
    write('M3/M3-3/README.md',f'''# M3-3：阿克曼定位导航与严格终点验收

使用本轮M3-2实际SLAM地图，AMCL根据地图和激光发布`map→odom`，轮式控制器发布`odom→base_footprint`。已知固定出生点对应地图(0,0,0)作为初始定位，Gazebo真值不进入TF、AMCL或控制，仅用于独立验收。

正式固定种子组完成{static['successes']}/10次严格通过，成功平均{f(static['mean_seconds'])}仿真秒；真值位置误差均值{f(static['mean_position_error_m'])}m、最大{f(static['max_position_error_m'])}m，朝向误差最大{f(static['max_yaw_error_rad'])}rad。每次目标路径超过5m且包含转弯，完整成败行见[本轮CSV](../optimization/report/all_attempts.csv)。历史2/3和本轮口径不同，旧结果保留，不能直接当成同条件百分点收益。

## 选型与参数

全局`SmacPlannerHybrid/REEDS_SHEPP`，局部为基于Humble RPP扩展的`smartcar_nav_checks::AckermannRPP`；最小规划半径0.65m，控制器在碰撞预测前把曲率限制到≥0.60m转弯半径，底盘桥再兜底。规划器、RPP和速度平滑器同时支持有界倒车，最大倒车速度0.20m/s；关闭原地旋转。相比前向Dubins，Reeds-Shepp可提供符合非完整约束的末端修正路径。MPPI也是可选方案，但本次没有把未做公平重复实测的方案宣称更优。

末端跟踪使用0.45m虚拟朝向参考，真实Nav2目标不变；0.60m内按0.7×目标距离减速（不强行提高更低的安全速度）。预测采用实际受限车辆弧线，终点附近不要求驶过真实目标。`controller_commands.csv`记录底盘限幅前的原始请求，用于量化控制器是否请求了不可实现的急转弯。

默认巡航0.32m/s，速度相关前视0.30～0.65m、前视时间1.2s；碰撞预测2.0s；xy容差0.05m、yaw容差0.10rad。独立验收更关注最终物理位置：≤0.15m且≤0.20rad、路径≥5m、保守包络无重叠、激光/真值样本充分。代价地图footprint另加0.08m规划余量，膨胀0.45m是软代价场；0.95m门比0.26+2×0.08=0.42m包络宽，膨胀半径不是一刀切禁行带。完整默认值→新值→理由见`config/changes.yaml`与带注释的`nav2_params.yaml`。

## 修复过的真实失败

1. 旧配置行为树绝对路径指向其他目录：launch现在根据当前checkout解析，原参数文件不被运行过程改写。
2. 前向导航进入位置容差但朝向差约14°，继续绕行后中止：完整倒车规划/跟踪链解决候选问题，仍以重复真值验收为准。
3. 反复启动时曾出现服务超时、TF停滞和旧路径起点：Fast DDS UDPv4候选仍只通过8/10。相同失败种子对照后，M3导航改用项目内官方CycloneDDS和本机单播配置；M1、方形与建图环境保持原设置。固定地图目标按最新TF转换，等待TF时不占用代价地图锁。对照、失败和运行库版本均保留。
4. Humble目标TF转换失败时曾出现车只走0.24m就Action成功。新增C++`ValidPoseGoalChecker`拒绝零/非有限/非单位四元数，始终同时检查xy和yaw。插件与上游接口兼容，独立回归测试覆盖实际失败形态；即使Action成功，外部真值门槛仍会拦截假成功。
5. 内岛拐角曾擦入保守包络：增加规划余量和软代价场。后续标准RPP候选即使静态9/10，仍有末端绕行碰外墙；因此没有采用，新增阿克曼曲率预测与末端朝向引导后重新完整验收，失败CSV全部保留。

```bash
bash scripts/build_ros.sh
bash scripts/install_m3_dds.sh
source scripts/m3_nav_env.sh
# 一条launch同时起Gazebo、地图、AMCL、Nav2
ros2 launch ./M3/M3-3/bringup.launch.py
# 与上一条二选一：自启并清理仿真，实际发送任意地图目标
bash scripts/run_m3_demo.sh static --goal 10,4,1.5707963268
# 批量严格验收，不开图形界面
.venv-ros/bin/python scripts/verify_navigation.py --runs 3
```

同一时刻只运行一个Gazebo实验。演示脚本会创建新结果目录并清理自身进程；不要后台叠加上一条launch。代价地图原始OccupancyGrid数组、全局路径、odom、真值、控制指令、行为树事件均有记录；图见[优化报告](../optimization/report/)。未见目标的测试、失败边界和统计置信区间一起报告，10/10也不代表所有目标都可达。
{common}''')
    table='|配置|严格成功/10|成功耗时(仿真s)|真值绕行额外(m)|指令转向TV(rad/m)|\n|---|---:|---:|---:|---:|\n'
    for s in dynamic:
        table+=f"|{s['profile']}|{s['successes']}/10|{f(s['mean_seconds'])}|{f(s['mean_extra_length_m'])}|{f(s['mean_steering_variation_rad_per_m'])}|\n"
    write('M3/M3-4/README.md',f'''# M3-4：动态实体障碍、三组实测与分步调优

导航开始3秒后通过Gazebo SpawnEntity生成0.6m实体箱，默认世界坐标(8.0,1.6)。雷达实际观测、物理模型可碰撞，同时由局部/全局障碍层更新；没有直接往代价地图画障碍。初始路径到箱子中心距离随每次结果保存，用于确认箱子确实挡路。位置、时机、尺寸和目标均可命令行修改。

{table}

正式A/B/B_speed/B_tuned共用AckermannRPP、曲率约束和末端跟踪，A/B是保守/激进两套参数，符合题面允许的两套极端参数方案。B_speed只降低B速度，用作中间诊断；B_tuned进一步调整前视与预测时间。标准RPP候选静态9/10与一次外墙包络越界作为根因证据另存，不混入正式参数对照。三组正式动态每组10次，不自动丢弃失败重抽。具体配置与结果见[分析报告](report.md)及[原始CSV](../optimization/report/all_attempts.csv)。

```bash
source scripts/m3_nav_env.sh
# 图形桌面：一个命令完整演示，自行起栈、发目标、延迟注入并清理
bash scripts/run_m3_demo.sh dynamic
# 考官指定另一个位置；可修改目标、delay、size
bash scripts/run_m3_demo.sh dynamic --obstacle-at 9.5,1.4 --delay 2.5
# 从头采集各组无障碍参考，再各跑10次动态对照并生成四指标
.venv-ros/bin/python M3/M3-4/scripts/run_benchmark.py --runs 10
# 本轮固定正式计划（包含10次默认静态）
.venv-ros/bin/python M3/optimization/run_qualification.py --suite main
```

严格成功判据与M3-3相同，并要求请求的障碍确实注入。时间只统计严格成功样本，从接受目标到Action结束，停车等待另列；绕行为真值轨迹积分减同配置成功无障碍参考均值，不能把失败半程当基线。转向TV为底盘桥reference计算的指令转向角总变化/真值距离，不冒充轮胎实测转角。所有失败保留在成功率分母，某组没有成功参考时绕行标N/A并解释。

四阶段截图来自实时ROS map/plan/scan/TF窗口，另有全部真值轨迹叠加图、四指标柱图、真实代价地图数组/图和控制曲线。已知静态方盒场景的几何间距是独立保守包络检查，不等同Gazebo接触传感器认证。随机位置、不同目标和目标占据的边界实测见`../optimization/`，不承诺任意动态目标都能避开。旧2026-11-16各10次数据和当时规划距离估计保留在历史results目录。
{common}''')
    write('M3/M3-4/report.md',f'''# M3-4：本轮严格真值实测分析

{table}

## ① 综合表现与代价

以上为同一地图、车辆、目标、障碍注入时机和200～209的Gazebo种子组，采用同一严格验收器。成功耗时、绕行与平滑度均只对严格成功样本取均值；失败完整进入成功率分母。每组只有10次，置信区间见`../optimization/report/summary.json`，不能从小样本推断任意现场成功率。比较应同时读取耗时与稳定性，而不是只挑一个最好看的指标。

## ② 实测失效边界

早期严格前向方案有终点朝向不符后绕行失败，安全余量不足时有内岛拐角包络越界；这些探索数据保留。另用0.8m箱占据目标世界(11,5)的独立边界试验验证不可达时退出和停车。该边界的最新原始数据与说明见[总报告](../optimization/REPORT.md)，不把“测试器观察到失败”说成避障成功。

## ③ 失败与重规划延迟

行为树FollowPath进入FAILURE的接收仿真时间，与随后第一条有效`/plan`接收时间配对。若该次没有FollowPath失败或后续没有有效路径，明确留空；目标占据时不可能仅靠重规划使目标可达。`failure_replans.json`保存事件配对。注入到周期性下一条plan的时间是另一个指标，不能冒称局部规划失败后的恢复延迟。上游原始日志仍保留，可核对ROS墙钟与仿真时间的区别。

## ④ 场景与具体参数选择

当前场景为约2m走廊、0.95m地图窄门、静止临时方盒。A巡航0.28m/s，B为0.65m/s/固定0.25m前视/0.5s预测；B_tuned为0.32m/s/速度相关0.30～0.65m前视/2s预测，并使用AckermannRPP的0.60m最小半径与0.45m末端参考。所有组共用0.08m规划padding、0.45m软膨胀、0.65m最小规划半径和0.05m/0.10rad目标容差。实际推荐需以本表和额外位置测试为依据；未测高速移动障碍、传感器失效或真实轮胎接触，不延伸结论。

## 分步调优

先完成阿克曼曲率预测和末端跟踪修复，再固定同一个AckermannRPP内核做参数对照。第一步只把B速度0.65降到0.32m/s，得到B_speed诊断组；第二步保持该速度，仅改前视策略和碰撞预测时间，形成B_tuned，并完整重跑10次动态。标准RPP候选的9/10与越界失败用于解释控制器改造，不冒充同内核参数调优的因果收益。每组参数快照与原始结果可对照，历史基线未删除。中间3次诊断不冒充10次验收，静态和动态结果不混成单一成功率。

## 四指标数据口径

本轮主绕行为实际世界真值轨迹积分减同配置无障碍成功参考均值，不再用历史`/plan`长度估计代替物理里程。参考成功样本量也在summary中给出；无成功参考时为N/A。平滑度使用指令转向TV，数值越低表示单位距离内指令转角变化少，不代表轮胎磨损已实测。原始OccupancyGrid、CSV、计划、哈希和完整成败列表可独立核验。
''')
    (report/'headline.json').write_text(json.dumps(dict(square=dict(position_mean_m=mean('truth_position_error_m'),position_sd_m=sd('truth_position_error_m'),yaw_mean_deg=mean('truth_angle_error_deg'),yaw_sd_deg=sd('truth_angle_error_deg')),map=map_info,static=static,dynamic=dynamic),indent=2))
    print('UPDATED_M3_REPORTS')


if __name__=='__main__': main()
