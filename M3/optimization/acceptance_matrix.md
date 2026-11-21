# M3题面要求与本轮证据索引

此页由当前JSON/CSV检查生成。通过的是本次记录和列明的条件；个人独立理解、现场指定目标以及实车性能仍需本人现场验证。

|题目|要求|当前结果与直接证据|
|---|---|---|
|M3-1|题面模型、阿克曼底盘、odom与几何一致|[包](../M3-1/src/smart_car_description/)保留original文件；[原件哈希与物理几何验证](report/model_provenance.json)；车体0.45×0.22、轴距0.28、轮距0.18、半径0.05m不变，后轴TF修正有说明|
|M3-1|2m闭环、10次、odom/真值CSV、均值±标准差|[当前统计/图](../M3-1/results/current_feedback/)；[原始20份CSV](../optimization/results/20261120_235742_qualified_feedback_rear/logs/)，表头t,x,y,theta；odom接收采样率均值约50.11Hz（按仿真接收窗口估计）|
|M3-1|TF树、发布者、固定/动态关系|[带标注树图](../M3-1/results/tf_tree_annotated.png)；配置frame_id为odom、child为base_footprint，M3-1不发map→odom|
|M3-2|自建长走廊、回环、难点、实际SLAM|[世界](../M3-2/worlds/scene.world)、[SLAM配置](../M3-2/config/)、[真实巡场与图](../M3-2/results/20261121_001551_qualified_mapping/)|
|M3-2|栅格、窄门、回环证据与局限|0.05m栅格、0.95m门、268节点/284边/17历史非邻接约束；[地图来源](../M3-2/maps/map_manifest.json)|
|M3-2|地图可被实际导航正确读取|[原生GetMap回验](../M3-2/results/map_semantics_final_20261121/roundtrip.json)，1600占据/12820未知/24784自由；PGM像素未修改|
|M3-3|同一SLAM地图、AMCL、一键启动、可换目标|[launch](../M3-3/bringup.launch.py)、[单命令演示](../../scripts/run_m3_demo.sh)，--goal可传任意地图目标；真值不进入定位|
|M3-3|至少3次且≥60%，路径>5m含转弯|默认完整10次严格10/10，[全部成败](../M3-3/results/runs.md)；新目标另见额外场景，不混入默认组|
|M3-3|每个非默认参数注释、调参前后数据|101项叶参数[旧值/新值/理由](../M3-3/config/changes.yaml)，[带注释YAML](../M3-3/config/nav2_params.yaml)、[分步实测](../M3-3/results/tuning_log.md)|
|M3-3|全局/局部代价地图、路径、速度与原话题|[实际图](report/costmaps.png)、[控制曲线](report/commands.png)、每次costmaps.json/plans.json/commands.csv/controller_commands.csv|
|M3-4|出发后2～4s实体注入、雷达可见、位置可改|默认--delay3，spawn实际时刻、激光与路径距离逐次保存；[演示入口](../../scripts/run_m3_demo.sh)|
|M3-4|两套极端参数各10次、差方案调优后10次|A/B/B_tuned各10次，[30行正式动态CSV](../M3-4/results/benchmark.csv)；早期速度/前视诊断各3次；上一版2秒预测十次另存，最后只收紧内部停车余量|
|M3-4|四指标、轨迹叠加、至少4帧过程|[四指标](report/metrics.png)、[全轨迹](report/trajectories.png)、[实际四帧与代价地图](../M3-4/results/process_sequence/)；主绕行为真值积分|
|M3-4|四问引用实测、重规划延迟、失效触发|[四问](../M3-4/report.md)、[逐步调参](../M3-4/results/tuning_log.md)、[边界](../M3-4/results/failure_boundary.md)、[延迟配对](report/replanning_detail.json)|
|M3-4|额外位置、不同目标、不可达边界|10次额外场景，[完整统计](extended_report/summary.json)；目标被箱体占据时检查失败退出与停车，不能计作到达成功|

## 共同验证与边界

TF2锁顺序回归与原生加载路径：[本机旧/新库回归](report/tf2_lock_regression.json)。每次controller_server、planner_server和amcl的实际库映射在该次native_runtime.json中，52次都已核对；系统dpkg仍显示旧版是因为修复只在项目进程内加载，并未修改M1系统环境。

独立成功门槛：Action成功且世界真值终点≤0.15m/0.20rad、路径>5m、数据充分、保守包络无重叠，动态场景要求实体注入成功。52次正式/诊断记录中控制器原始请求曲率越界为0；几何采样不等于接触传感器认证。

10项Python与4项原生C++检查、M1处理语义与通信链路回归、实际桌面演示的退出码见[最终验证目录](../../M3/optimization/results/20261121_152430_terminal_refinement/)。不同ROS通信实现、阈值和中途停止的候选在[完整审计](report/experiment_audit.json)单列保留，不混入最终成功率。10次全成功也不能证明所有目标成功。

当前M3导航只在本机使用CycloneDDS单播；M1保留原环境；M3方形、建图保留原DDS并加载TF2修复。依赖版本锁见[navigation-packages.lock](../runtime/navigation-packages.lock)。全新环境按根README安装；完整离线包提供DDS缓存与原始bag。答辩准备/PDF只在本地，M5/M6未继续验收。

## 终点修正版与M1完整验收

本次最终B_tuned内部XY停车从0.05收紧至0.02m，外部0.15m/0.20rad不变。新动态10/10和新静态10/10来自固定种子200～209的完整批次。A/B和原中间组保留历史实测，没有冒称全部重跑。

[误差预算与旧失败](../../evidence/M3-terminal-refinement/20261121_152129/setup_and_error_budget.json)；[新固定批次](../../M3/optimization/results/20261121_152430_terminal_refinement/validation.json)；[实际用户一键演示](../../evidence/M3-deployment/20261121_155402/verification.json)；[该次实际TF树](../../evidence/M3-deployment/20261121_155402/actual_nav_tf.pdf)。展示不计入正式十次分母，控制配置和核心源码已与冻结版本逐项比对。

[M1四题完整复测](../../M1/ACCEPTANCE.md)及[原始报告](../../evidence/M1-acceptance-v2/20261121_154558/results.json)覆盖实际滤波、隔离/就绪、六图像素及TF/时钟、五组图像语义、四组性能和60秒持续达标。

M3的10项Python与4项原生C++回归日志在[本轮整理证据](../../evidence/M1-M3-terminal-release/20261121_155100/)中；相机前端0.01m余量按当前62条记录重新复核。不能把十次通过解读为任意现场零风险。
