# M3-4当前动态障碍现场入口

```bash
bash scripts/run_m3_demo.sh dynamic
bash scripts/run_m3_demo.sh dynamic --obstacle-at 9.2,1.3 --runs 2
bash scripts/run_m3_demo.sh dynamic --obstacle-at 11,5 --obstacle-size .8 --timeout 90
# 当前完整三组各10次与匹配无障碍参考
.venv-ros/bin/python M3/M3-4/scripts/run_benchmark.py --runs 10
```

默认世界(8,1.6)、0.6m实体箱，首次/odom实际运动后3秒生成，激光真实观测更新代价地图；坐标是世界坐标，导航goal是map坐标，不混用。原生中间件/TF2、曲率、footprint、目标与外部验收一致。A/B允许同一规划器两套极端参数，三组当前同内核各10次，失败不重抽。

当前[30次动态CSV](results/benchmark.csv)、[四指标](results/metrics.png)、[真值轨迹](results/trajectories.png)、[四问](report.md)、[调参/历史](results/tuning_log.md)、[失败边界](results/failure_boundary.md)均可追溯。当前运行的真实ROS应用窗口AVI与四阶段图见[现场证据索引](../../docs/showcase_acceptance.md)；查看器只读，不写代价地图或控制，不把2D应用窗口说成Gazebo3D录像。

本轮代理选择新点模拟考官临时改题，不能冒充实际考官随机考核。旧版目标接受+3秒批次另存，不混入当前运动起点+3秒统计。有限样本与已测场景不能保证任意位置成功。
