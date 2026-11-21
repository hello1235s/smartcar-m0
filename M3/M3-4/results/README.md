# 当前动态避障结果入口

- benchmark.csv：最终A/B/B_tuned三组各10次，失败保留。
- metrics.png与trajectories.png：本轮四指标和全部实际轨迹。
- process_sequence/：最终发布查看器一次严格通过的四阶段与代价地图，来源与哈希见source_manifest.json；不计入正式统计分母。
- tuning_log.md：速度、前视策略、预测时间的分步数据。
- failure_boundary.md与replanning_summary.json：失败边界及不同时间口径。
- ../report.md与../../optimization/acceptance_matrix.md：四问与逐项题面证据。

历史日期目录、matched_comparison/、matched_baselines.json和replanning_after_failure.json属于2026-11-16的旧口径，保留作过程证据，不与当前统计混算。最新完整数字以../../optimization/report/为准。

查看器的琥珀色虚线仅标注SpawnEntity成功确认的请求区域；红点来自实际scan，命中区域的点只放大显示。标注不写入代价地图，也不参与控制。绿色足迹及虚线padding来自该次参数配置。
