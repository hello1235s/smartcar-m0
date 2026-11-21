# 当前SLAM质量报告入口

以下均来自本轮实际巡场，历史日期目录保持原样。

- [地图质量图](20261121_001551_qualified_mapping/quality/map_quality.png)与[逐项测量](20261121_001551_qualified_mapping/quality/quality.json)：0.05m栅格、19个自由格的窄门，即0.95m；190个北墙占据点共线、未检出相隔超过两格的分离重影。共线是栅格结果，不是亚栅格精度或零漂移证明。
- [实际位姿图分析](20261121_001551_qualified_mapping/graph_analysis.json)：268节点、284边、17条历史非邻接约束，不等同17次独立回环检测事件。原posegraph/data在同目录。
- [原生地图加载回验](map_semantics_final_20261121/roundtrip.json)：1600占据、12820未知、24784自由格。仅修正YAML阈值，SLAM像素未改。
- [当前地图与来源](../maps/)：PGM/YAML、地图来源清单及当前预览的逐字节来源。

原始录包保存在同次实验bag目录与独立离线交付包，未提交Git。观测到的单格墙面轮廓不是实体墙厚，图像也不能证明扫描采样之间绝无误差。
