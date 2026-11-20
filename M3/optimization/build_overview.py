"""Reconcile top-level delivery documents with current, explicitly sourced results."""
import json
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]


def main():
    headline=json.loads((ROOT/'M3/optimization/report/headline.json').read_text())
    square=headline['square']; static=headline['static']; dynamic=headline['dynamic']; map_info=headline['map']
    default=next(s for s in dynamic if s['profile']=='B_tuned')
    rows='\n'.join(f"|{s['profile']}|{s['successes']}/{s['attempts']}|{s['mean_seconds']:.3f} s|{s['mean_extra_length_m']:.3f} m|{s['mean_steering_variation_rad_per_m']:.3f} rad/m|" if s['mean_seconds'] is not None and s['mean_extra_length_m'] is not None else f"|{s['profile']}|{s['successes']}/{s['attempts']}|N/A|N/A|N/A|" for s in dynamic)
    extra_path=ROOT/'M3/optimization/extended_report/summary.json'
    extended=json.loads(extra_path.read_text()) if extra_path.exists() else []
    extension='\n'.join(f"|{s['group']}|{s['successes']}/{s['attempts']}|{s['minimum_clearance_all_attempts_m']:.4f}|" for s in extended)
    text=f'''# M3优化实测总报告

本轮在Ubuntu 22.04、ROS2 Humble、Gazebo Classic 11、VMware 6 vCPU中实际运行。结果对应当前后轴TF与M3-2新建地图；历史2026-11-16结果单独保留。源码、逐次参数、运行库、地图哈希和完整成败记录可独立核对。不是实车验收，也不把有限样本称为“完美”。

## 结果

- 方形反馈闭环10次：后轴真值位置误差{square['position_mean_m']:.6f}±{square['position_sd_m']:.6f}m，朝向{square['yaw_mean_deg']:.6f}±{square['yaw_sd_deg']:.6f}°，±为样本标准差。
- 当前SLAM图：0.05m栅格、0.95m地图窄门、{map_info['graph']['vertices']}节点/{map_info['graph']['edges']}边/{map_info['graph']['historic_constraints']}条历史非邻接约束。北墙共线只反映栅格尺度，不是零误差声明。
- 默认静态导航：严格{static['successes']}/10，成功平均{static['mean_seconds']:.3f}仿真秒，最大真值位置/朝向误差{static['max_position_error_m']:.4f}m/{static['max_yaw_error_rad']:.4f}rad。
- 标称动态B_tuned：严格{default['successes']}/10；完整参数对照如下。

|配置|严格成功|成功平均耗时|实际额外路径|指令转向TV|
|---|---:|---:|---:|---:|
{rows}

依据与限制见[完整CSV](report/all_attempts.csv)、[分组统计与置信区间](report/summary.json)、[口径定义](report/method.json)、[四指标图](report/metrics.png)、[全部轨迹图](report/trajectories.png)、[真实代价地图](report/costmaps.png)和[控制曲线](report/commands.png)。每组10次，10/10的Wilson 95%区间下限仍约72.2%，不是任意环境成功保证。

## 实现变化与因果边界

1. 修正参考点：后轴中点与控制器积分点一致，base_link固定向前0.14m。物理尺寸不变，规划footprint同步平移，SLAM实际重建。
2. 定时巡航改为odom反馈、加减速、单调路径进度和终点联合判定；真值仅记录。新速度较慢，因此不能把新旧闭合改善全算作反馈收益。新后轴误差统一到车体中心后约0.02156±0.00468m，历史0.2843±0.0408m，两者采用同一物理参考点才可对照。
3. 同速参考点/控制方式消融的单次探索全部保留：原参考定时约0.1314m、后轴参考定时约0.1415m、原参考反馈约0.0200m、后轴参考反馈约0.0185m。单次不作为显著性检验，只说明主要收益与反馈相关，不能把它归功于移动坐标原点。
4. Nav2使用SmacHybrid/Reeds-Shepp、AckermannRPP、有界倒车平滑链，关闭原地旋转。控制器在碰撞预测之前限制曲率，并用0.45m虚拟末端参考引导朝向；真实目标不移动，近端按实际目标距离减速。默认xy/yaw容差0.05m/0.10rad，外部真值验收≤0.15m/0.20rad，不靠放宽容差过关。
5. 默认0.08m规划padding、0.45m软膨胀，给定位、栅格和跟踪误差留余量。早期内岛拐角包络越界失败保留，规划余量不用于缩小独立评价车身。
6. 修复Humble目标检查路径的TF失败假成功：无效目标四元数被新增插件拒绝。原错误曾在仅行驶约0.24m时返回Action成功，被独立真值门槛拦截。10项Python测试与3项C++回归（位姿有效性、车辆曲率/末端速度约束、标准/扩展插件加载）通过。
7. Fast DDS UDPv4候选仍发生TF停滞，只通过默认静态8/10；该轮完整保留。相同失败种子下的通信对照后，M3导航采用项目内官方CycloneDDS、本机单播；M1、方形与建图环境不改。固定地图目标按最新TF转换，等待时不占用代价地图锁。行为树路径按当前checkout解析，消除旧目录依赖。

地图序列化还通过原生Nav2回验：保留原SLAM像素，仅修正free_thresh 0.25→0.196，使12820个灰色未知格不再错误变成自由格。原生map_server加载后1600占据/12820未知/24784自由与原PGM完全一致。当前正式统计均使用修正后的同一PGM与YAML哈希，修正前候选单列保留。

## 新位置、新目标与边界

|独立场景|严格到达次数|全部尝试最小几何间距(m)|
|---|---:|---:|
{extension}

目标被0.8m箱体占据的场景预期不可达；应检查Action失败/超时、最终速度和几何间距，不把“正确拒绝”混进到达成功率。独立场景的原始CSV、具体坐标/目标/尺寸和失败原因见`extended_report/`及对应实验快照。随机位置仅是额外覆盖，未测高速移动障碍或真实道路，不扩展结论。

## 指标与证据

严格成功同时要求Action成功、独立世界真值终点合格、有效路径超过5m、激光/真值样本充分、保守轮组包络没有与已知方盒重叠，动态场景还要求实体注入成功。碰撞项是基于采样世界位姿和已知几何的独立包络检查，不是Gazebo接触传感器认证。

主路径长度为世界真值积分，额外路径减同一配置成功无障碍参考均值；无成功参考时为N/A。耗时是接受目标到Action结束的仿真时间，不包含停车等待。转向TV来自底盘桥reference的`atan(0.28*omega/v)`，除以真值距离，不冒充转向关节实测。

保存实际/plan、odom、world_truth、map估计、指令、几何间距、行为树事件和全局/局部OccupancyGrid数组。周期性注入后下一条plan与FollowPath失败后有效新plan分别记录；没有失败或没有后续有效plan时保留空值。全部失败在成功率分母，不只挑成功截图。

## 复现

```bash
bash scripts/build_ros.sh
bash scripts/install_m3_dds.sh
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
'''
    (ROOT/'M3/optimization/REPORT.md').write_text(text,encoding='utf-8')
    readme=ROOT/'README.md'; content=readme.read_text(encoding='utf-8')
    replacements={
      'M3-1':f"| M3-1 | odom反馈十次；真值闭合{square['position_mean_m']:.4f}±{square['position_sd_m']:.4f}m、{square['yaw_mean_deg']:.2f}±{square['yaw_sd_deg']:.2f}° | [说明](M3/M3-1/README.md) · [优化实测](M3/optimization/REPORT.md) |",
      'M3-2':f"| M3-2 | 后轴TF修正后真实重建SLAM；0.95m门，268节点/284边/17历史约束 | [说明](M3/M3-2/README.md) · [地图与来源](M3/M3-2/maps/) |",
      'M3-3':f"| M3-3 | AMCL、阿克曼Nav2、有效位姿检查；严格{static['successes']}/10 | [说明](M3/M3-3/README.md) · [全部成败](M3/optimization/report/all_attempts.csv) |",
      'M3-4':f"| M3-4 | 动态实体障碍，A/B/B_tuned各10次：{'/'.join(str(s['successes']) for s in dynamic)}次通过；另有独立位置/目标与边界 | [说明](M3/M3-4/README.md) · [分析](M3/M3-4/report.md) · [当前对照](M3/optimization/report/) |"}
    for key,line in replacements.items(): content=re.sub(r'^\| '+key+r' \|.*$',lambda _:line,content,flags=re.M)
    content=re.sub(r'^数据口径、失败记录和限制见.*$', '当前M3使用严格真值终点验收与实际轨迹积分，见[优化总报告](M3/optimization/REPORT.md)；旧66.7%、8/3/7等成绩保留为历史，不能与新口径直接混算。验收边界见[清单](docs/M1_M3_验收清单.md)。',content,flags=re.M)
    content=content.replace('三个包。','四个包（新增smartcar_nav_checks目标检查插件）。')
    marker='\n## M3本轮更新\n\n实现与实测已更新；M1原实现保留，并执行共享环境回归。当前代码、地图、配置、实验结果、图表和复现入口以M3/optimization/REPORT.md为索引。答辩材料与PDF只在本地。\n'
    if '## M3本轮更新' not in content: content+=marker
    readme.write_text(content,encoding='utf-8')
    disclosure=ROOT/'AI_USAGE.md'; content=disclosure.read_text(encoding='utf-8')
    content=content.split('\n## M3本轮优化补充')[0]
    content=re.sub(r'^\| M3-3 \|.*$',lambda _:f'| M3-3 | 阿克曼Nav2、AMCL、严格真值门槛和无效位姿修复 | 默认静态{static["successes"]}/10；所有失败与探索记录保留 |',content,flags=re.M)
    content=re.sub(r'^\| M3-4 \|.*$',lambda _:'| M3-4 | 实体注入、极端参数对照、分步调优与真值四指标 | 三组各10次，另测新位置、目标与不可达边界 |',content,flags=re.M)
    content+='\n## M3本轮优化补充\n\nCodex继续参与后轴参考点核对、odom反馈控制、SLAM重建、严格真值验收、Humble无效目标位姿插件、DDS启动故障处理、分步参数试验和报告更新。新结果见M3/optimization/REPORT.md；它们来自重新运行的Gazebo进程，不是把历史结果改名。本人独立理解和现场操作仍由本人确认。\n'
    disclosure.write_text(content,encoding='utf-8')
    checklist=ROOT/'docs/M1_M3_验收清单.md'
    content=checklist.read_text(encoding='utf-8')
    content=content.split('\n## M3本轮验收索引')[0]
    notes={
      '3.':f'3. M3-1本轮10次反馈闭环，真值位置{square["position_mean_m"]:.4f}±{square["position_sd_m"]:.4f}m；统一参考点与新旧速度差异见优化总报告。',
      '4.':'4. M3-2本轮真实重建图268节点、284边、17条历史非邻接约束；0.05m栅格质量不等同亚栅格定位精度。',
      '5.':f'5. M3-3本轮默认静态严格{static["successes"]}/10，要求真实终点位置≤0.15m、朝向≤0.20rad；旧2/3是历史不同口径。',
      '6.':'6. M3-4本轮主绕行改为真值轨迹积分，匹配同配置成功无障碍均值；没有有效参考时记N/A。历史/plan估计未冒充真值。'}
    for number,note in notes.items(): content=re.sub('^'+re.escape(number)+r' .*$',lambda _:note,content,flags=re.M)
    content+='\n## M3本轮验收索引\n\n当前M3以M3/optimization/REPORT.md及report/all_attempts.csv为准；方形10次、默认静态10次、三组动态各10次、额外位置/目标和无解边界分别报告。真值不输入控制或定位；有限样本、几何包络与实车边界均保留。M1历史指标不被本轮M3成绩覆盖，M5/M6未继续验收。\n'
    checklist.write_text(content,encoding='utf-8')
    sources=ROOT/'THIRD_PARTY.md'
    content=sources.read_text(encoding='utf-8').split('\n本轮增加本仓库C++插件')[0]+'\n本轮增加本仓库C++插件smartcar_nav_checks（Apache-2.0），使用Nav2 GoalChecker公开接口；未修改apt安装的Nav2二进制。后轴运动学、Humble目标转换失败链路和Fast DDS 2.6配置的官方源码/文档链接见M3/optimization/REPORT.md，精确运行版本随实验runtime_versions.txt保存。\n'
    sources.write_text(content,encoding='utf-8')
    print('UPDATED_OVERVIEW_AND_DELIVERY_DOCS')


if __name__=='__main__': main()
