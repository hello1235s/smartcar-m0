# M3-3当前自主导航与现场目标

```bash
source scripts/env.sh
bash scripts/run_m3_demo.sh static
# 原生RViz中按G，拖选地图目标和朝向；结果按实际目标记录
bash scripts/run_m3_demo.sh target
# 也可由命令行给出地图x,y,yaw（弧度）
bash scripts/run_m3_demo.sh static --goal 10,5.5,1.5707963268
```

一条命令起仿真、原SLAM地图、AMCL、Nav2与目标记录。原生RViz组件窗口提供内部渲染截图，解决XWayland外部读回全黑的问题，不是自绘地图替代RViz。地图、车体与定位输入不变；新增末端对齐参考避免微型倒车折返。严格门槛仍为Action成功、真值15cm/0.20rad、路径>5m、激光充分与独立几何无重叠。

当前十次与最大误差见[十次表](results/runs.md)；至少三项默认→新值→理由见config/nav2_params.yaml、config/changes.yaml和[配置数据](results/tuning_log.md)。[总报告](../optimization/REPORT.md)包含真实costmap、plan/轨迹、速度/角速度曲线及失败；[最新指南验收](../../docs/showcase_acceptance.md)包含两次实际鼠标目标与记录。
