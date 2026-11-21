# 额外场景与失败边界

|场景|到达/次数|Action状态|最后线速度m/s|几何重叠采样|
|---|---:|---|---|---:|
|heldout_obstacle_east|2/2|4,4|0.0000,-0.0001|0|
|heldout_obstacle_gate_exit|2/2|4,4|0.0000,0.0000|0|
|heldout_goal_northeast|2/2|4,4|0.0003,-0.0000|0|
|heldout_goal_far_northwest|2/2|4,4|-0.0000,0.0000|0|
|boundary_blocked_goal|0/1|None|-0.0000|0|
|boundary_close_front|0/1|6|0.0001|0|

目标被0.8m实体箱覆盖时预期不可达，不能把退出停车当作到达成功。Action状态为None表示未取得终态；若原始failure_reason为simulation_timeout，则由试验器90秒看门狗触发取消与停车，不冒称Nav2主动判定无解。近前方突发箱测试局部阻挡、重规划与停车；其结果单独报告，不能从单次推断“所有近障都必失败”。原始位置/目标/尺寸/时机见每组快照。
