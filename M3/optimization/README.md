# M3优化：复现、证据和指标口径

最终结论读[实测总报告](REPORT.md)，逐项要求读[验收索引](acceptance_matrix.md)。历史候选、初始化失败和人为中止的批次全部保留在results及[审计](report/experiment_audit.json)，不混入当前成功率。

## 环境和短演示

从仓库根目录执行，先按根README准备Ubuntu 22.04、ROS2 Humble和`.venv-ros`，再运行：

```bash
bash scripts/build_ros.sh
bash scripts/install_m3_runtime.sh
source scripts/env.sh
# 以下每次只运行一条，结束后再开始下一条
bash scripts/run_m3_demo.sh square
bash scripts/run_m3_demo.sh static
bash scripts/run_m3_demo.sh dynamic
# 地图坐标目标；实体障碍是Gazebo世界坐标
bash scripts/run_m3_demo.sh static --goal 9,6,3.1415926536
bash scripts/run_m3_demo.sh dynamic --obstacle-at 9.5,1.4 --delay 2.5
```

导航运行器自动配置项目内CycloneDDS。若另开终端观察导航话题或手工launch，先`source scripts/m3_nav_env.sh`，再设置该次`ROS_DOMAIN_ID`。默认单次演示domain180、Gazebo端口11382。此配置仅使用本机单播；连接开发板/其他电脑需要另行配置，不适用于跨机ROS发现。M1保留原环境；M3方形、建图保留原DDS并加载TF2修复，请在各自新终端`source scripts/env.sh`。

`M3/runtime/navigation-packages.lock`固定本次amd64虚拟机使用的6个官方ROS运行包（含TF2修复）版本；项目内解包，不需sudo、不替换系统Nav2二进制。完整离线交付包提供`m3-dds-debs`缓存及SHA256，将其放到`vendor/m3-dds-debs`后可执行`bash scripts/install_m3_runtime.sh --offline`。已有ROS、GUI、编译器等基础依赖仍按根README准备；这些amd64离线包不用于Jetson的ARM64系统。

短演示保存结果后窗口停留8秒，再自动清理自身进程，便于看清停车；展示停留不计入任何导航指标。批量实验默认不加这段停留。

实时窗口按C切换全局/局部代价地图。绿色显示TF估计位姿与该次配置的footprint，虚线显示规划padding。四阶段截图按初始plan的弧长触发，不依赖向东行驶；“检测”帧须先读到真实SpawnEntity成功日志，再收到注入后的激光区域命中。日志和已知障碍位置只决定截图时机，查看器没有速度/代价地图发布器，不参与控制。独立到达与几何验收仍只读实际记录。

手动附着查看器时，可用`--confirmation-log <该次trial.log>`指定注入确认日志；没有确认时仍显示ROS话题，但不伪称已检测到新障碍。当前发布的四帧来源见results/process_sequence/source_manifest.json；额外图形演示与每组10次性能统计分别标注。

## 完整重复实验

所有Gazebo实验顺序执行；全局锁和存活进程检查阻止叠加运行。下面各条执行完再运行下一条：

```bash
source scripts/env.sh
.venv-ros/bin/python M3/optimization/run_qualification.py --suite main
.venv-ros/bin/python M3/optimization/run_qualification.py --suite tuning
.venv-ros/bin/python M3/optimization/run_qualification.py --suite extended
```

main固定49次：默认静态10次，A/B无障碍参考各3次，A/B/B_tuned动态各10次，速度单改诊断3次。tuning另做前视单改诊断3次；extended另做10次新位置、新目标和边界。参数快照、地图PGM/YAML、控制器URDF、运行库版本/哈希、源码哈希、种子和所有成败均随每组保存。正常导航失败保留并继续计划；目标未被接受、进程异常等基础设施失败立即停止，不自动抽一个成功替换。

A/B/B_tuned均用同一AckermannRPP内核，A为0.28m/s/自适应前视/2s预测，B为0.65m/s/固定0.25m前视/0.5s预测，B_tuned为0.32m/s/自适应前视/2s预测。调参链分四步：B→B_speed只降速度，→B_lookahead只改前视策略，→B_horizon只改预测时间，→B_tuned只将内部XY停车余量0.05→0.02m；中间各3次，不宣称显著性，也不承诺每一步都有可检测收益。

运行器会打印各次manifest路径。把main和tuning两个完整manifest合并后分析，extended单独分析，例如将下方占位路径换成本次实际路径：

```bash
.venv-ros/bin/python M3/optimization/merge_manifests.py \
  --out tmp/main_and_tuning.json <main_manifest> <tuning_manifest>
.venv-ros/bin/python M3/optimization/analyze_qualification.py \
  --manifest tmp/main_and_tuning.json --out M3/optimization/report
.venv-ros/bin/python M3/optimization/replanning_report.py \
  --manifest tmp/main_and_tuning.json
.venv-ros/bin/python M3/optimization/analyze_qualification.py \
  --manifest <extended_manifest> --out M3/optimization/extended_report
```

只想重采题面三组正式对照，可运行`M3/M3-4/scripts/run_benchmark.py --runs 10`，它会先采同配置无障碍参考，再采三组动态并输出独立分析目录。不要拿不同地图、容差、内核或未完成批次拼成新的成功率。当前已发布分析的原manifest路径记在[method.json](report/method.json)中。

## 方形、建图和回归

```bash
.venv-ros/bin/python scripts/verify_square.py
.venv-ros/bin/python M3/optimization/run_square_trial.py \
  --mode timed --laps 10 --label matched_timed_rear
# 不替换当前已验收导航地图
.venv-ros/bin/python scripts/verify_mapping.py --no-promote
.venv-ros/bin/python -m unittest discover -s M3/tests -v
ctest --test-dir build_ros/smartcar_nav_checks --output-on-failure
.venv-ros/bin/python M1/M1-4/semantic_check.py
.venv-ros/bin/python scripts/verify_m1_chain.py
```

同速定时/反馈均使用0.28/0.18m/s、相同后轴参考和2m外包络圆角轨迹。原高速度历史成绩保留，但不作为单一参数的公平因果对照。反馈仅用odom；物理位姿复位发生在两次试验之间，不用真值修正odom。

SLAM来自实际巡场和序列化图。地图晋级检查包含墙体、门、历史图约束和原生Nav2加载分类回验；灰205必须保持未知，不能被YAML阈值误读成自由。当前PGM像素从未为美化或绕障而修改。原始bag与大型数据在Ubuntu及完整本地交付包，Git保留图、地图、CSV/JSON和关键日志。

## 看数据时容易混淆的地方

- 严格成功同时要求Action成功、真实停车位置/朝向≤0.15m/0.20rad、路径超过5m、样本充分且保守包络无几何重叠；动态场景还需真实实体注入。当前默认内部目标容差0.02m/0.10rad，A/B历史基线保留0.05m。真值只独立评分，不进入TF、SLAM、AMCL或速度控制。
- 时间是接受目标到Action结束的仿真时间。真值距离积分覆盖保存的记录窗口，含约0.8s停车等待；绕行减同配置成功无障碍参考均值。没有成功参考时记N/A，负差值保留。墙钟受VM负载影响，不和仿真秒混用。
- 平滑度是底盘reference指令转向角`atan(0.28*omega/v)`的总变化除以真值距离；不是转向关节或轮胎磨损实测。`controller_commands.csv`另记录底盘桥限幅前的原始请求，用于核对控制器自身的曲率约束。
- 已知世界方盒和采样真值的保守几何包络检查不是接触传感器认证，不能证明采样间隔内绝无碰撞。所有组采用相同口径。
- 局部控制错误日志→下一有效plan用接收墙钟配对；BT FollowPath FAILURE→plan另存接收仿真时间。注入后周期性下一条plan不是故障恢复延迟。空值表示没有可配对事件，不能填0秒。
- 四帧和实际代价地图来自实时ROS查看器。原PNG、原始OccupancyGrid数组、plan、scan/TF计数、轨迹和来源清单一起保留；未使用理想路径重画结果。
- 相同Gazebo种子不保证AMCL采样与线程调度逐位一致。10/10只是10个样本，Wilson区间和额外失败边界一并报告。现场换目标与实际车辆仍需验证。

答辩Markdown/PDF单独本地保存，不在GitHub。M1功能源码保持原实现，本轮增加共享环境回归；M5/M6没有继续交付。

## 前置相机额外审计

原车相机比车体前端凸出0.01m，常规独立评分明确检查车体/轮组包络。另对同一批原始真值采样扩展前界到后轴x=0.375m，单独保存camera_margin_audit.json，不重写原始成绩。可用`audit_camera_margin.py --main <合并manifest> --extended <扩展manifest>`复算；仍是离散已知几何检查，不能当作接触传感器认证。

## 终点余量修正与M1全项复测

原9/10批次与15.1523cm失败记录完整保留；终点修正仅收紧内部停车，不变更15cm/0.20rad外部验收。新B_tuned独立重跑动态10次、静态10次，A/B原基线和附加场景未冒称重测。误差预算和新清单见本轮report及evidence/M3-terminal-refinement。M1四题另以scripts/verify_m1_acceptance_v2.py重测，含实际滤波、两命名空间、非默认外参像素核对、四组性能和60秒持续窗口，详见根README与M1/ACCEPTANCE.md。
