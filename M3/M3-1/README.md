# M3-1：坐标系与十次里程计试验

使用题面原车构建 `smart_car_description`，40×40m 自建平地。轴距0.28m、轮距0.18m、轮半径0.05m、车体0.45×0.22m不变。保留 `*.original.*`。Humble 2.54 控制器轮对索引为 RIGHT/LEFT，题面原配置 LEFT/RIGHT 会造成明显误差；运行配置改正顺序，并通过原有底盘适配器将公共 `/cmd_vel` 转为带时间戳的 controller reference。相机渲染默认关闭，激光不关闭。

```bash
bash scripts/build_ros.sh
source scripts/env.sh
.venv-ros/bin/python scripts/verify_square.py
```

阿克曼不能原地转。采用2m外包络的圆角正方形，圆角半径0.65m，直段0.7m。直段速度0.6m/s、时间1.167s；每个90°圆弧速度0.35m/s、时间 π×0.65/(2×0.35)=2.917s。计入内轮约束，中心最小半径约 `0.28/tan(0.5236)+0.18/2=0.575m`；0.65m留有余量。停车和复位均不使用真值校正 odom；每圈只把物理车辆放回同一已知起点。

十次修正后实测：odom闭合位置误差 `0.2274 ± 0.0411m`，Gazebo真值闭合误差 `0.2843 ± 0.0408m`；角度分别 `12.71 ± 1.87°` 和 `15.80 ± 2.37°`，均为样本标准差。原左右顺序试验真值误差 `1.1957 ± 0.0313m`，保留原始失败数据，不删除或混入新均值。

`results/20261116_210401/` 保存修正后20份CSV、每圈统计、双轨迹图及所用配置。CSV列 `t,x,y,theta`，t来自仿真时钟；/odom目标50Hz，frame=odom、child=base_footprint，真值来自/gazebo/model_states。曲线闭合误差不等于定位误差：开环时间控制、转向建立过程和轮胎接触都会影响轨迹，需要用双源数据区分，不能仅用odom“自证准确”。

`results/tf_tree_annotated.png` 标注变换类型与发布者。map是SLAM/定位的全局一致坐标系；odom连续但累积漂移；base_footprint用于地面投影；base_link是车体坐标；lidar/camera与车体的固定关系由URDF提供。M3-1没有map→odom，M3-2由slam_toolbox发布，M3-3改由AMCL发布。
