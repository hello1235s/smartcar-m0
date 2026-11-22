# 当前M3-4四问分析

|方案|成功/10|成功耗时s|额外路径m|指令转向TV rad/m|
|---|---:|---:|---:|---:|
|A|10/10|48.8300|0.1356|0.8745|
|B|8/10|37.7250|0.4499|1.4670|
|B_tuned|10/10|44.2900|0.1293|0.7610|

① 同时比较成功率、耗时、绕行、指令转向TV，不能只挑一项。② 当前实际目标占据边界见results/failure_boundary.md；修复前的末端超时也保留。③ 错误到新plan的配对、空值与最终能否脱困见逐次JSON。④ 在已测走廊/窄门与静止临时箱体场景下选择具体配置，不能外推到高速移动障碍。

完整依据见[当前总报告](../optimization/REPORT.md)、[全部CSV](../optimization/report/all_attempts.csv)、[失败逐例](../optimization/report/failure_cases.md)、[重规划配对](../optimization/report/replanning_detail.json)与[配置/历史取舍](results/tuning_log.md)。
