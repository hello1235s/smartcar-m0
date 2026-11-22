# M3-1：阿克曼坐标系与里程计反馈闭环

从题面原车建立`smart_car_description`：车体0.45×0.22m、轴距0.28m、轮距0.18m、轮半径0.05m和转向限位±0.5236rad不变。保留`*.original.*`。Humble控制器轮序按RIGHT/LEFT适配，公共`/cmd_vel`经原底盘桥转换为控制器带时间戳的reference。

## 本轮改进与十次真值结果

原来按时间切换直行和转弯；现在`ForwardTracker`仅用`/odom`反馈控制2m外包络圆角正方形，圆角半径0.65m、直段0.7m。加入加减速、终点延伸和位置/朝向同时判定，防止刚出发因起终点重合而提前结束。直行0.28m/s、转弯0.18m/s，实际每圈35.23秒。Gazebo真值只记录和评价，不输入控制，也不拿它修正odom。

|10次结果|均值|样本标准差|
|---|---:|---:|
|后轴真值闭合位置(m)|0.018285|0.005359|
|真值闭合朝向(°)|1.637736|0.191802|
|odom闭合位置(m)|0.017695|0.001194|
|odom闭合朝向(°)|3.675453|0.063374|

原始CSV与每圈控制记录：[本轮十次](../optimization/results/20261120_235742_qualified_feedback_rear)。旧的2026-11-16十次数据仍在`results/20261116_210401/`，旧真值位置0.2843±0.0408m、角度15.80±2.37°。新旧速度和参考点不同，因此不能把全部改善归因于单一参数。统一到车体中心后，本轮闭合位置约0.02156±0.00468m。低速定时控制与反馈控制的消融样本及完整来源见[优化报告](../optimization/REPORT.md)。改善有时间代价，不冒称轮式里程计本身已达到厘米级定位精度。

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
.venv-ros/bin/python M3/optimization/run_square_trial.py \
  --mode timed --laps 10 --label matched_timed_rear
```

## 来源、AI参与与现场边界

使用题面车辆与历史文件，物理尺寸未缩小。Codex参与实现、调参、真实进程验证和文档整理；本人独立复现与逐行理解程度需本人确认。见[AI使用说明](../../AI_USAGE.md)和[验收清单](../../docs/M1_M3_验收清单.md)。全部M3结果为Gazebo仿真，不宣称实车道路性能；旧结果和失败样本保留，不代表任意目标都能成功。


## 最新展示指南工程补齐

现场入口、实际RViz/SLAM录像、临时目标与新障碍、有限样本边界见[工程验收](../../docs/showcase_acceptance.md)。所有代码与实验由Codex协助；本人独立理解、操作和现场考官验收不能由自动测试代替。
