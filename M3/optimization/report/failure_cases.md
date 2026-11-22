# 最终批次失败逐例证据

这里只索引最终主对照和额外场景中的全部未到达记录；历史候选另在experiment_audit.json。日志计数是重复消息数，不是独立故障次数。模式匹配只描述观察，不替代根因证明。

## formal_dynamic_B / run_03

[原始结果](../results/20261122_132446_showcase_qualified_formal_dynamic_B/run_03/result.json) · [导航日志](../results/20261122_132446_showcase_qualified_formal_dynamic_B/run_03/navigation.log) · [原生TF2加载](../results/20261122_132446_showcase_qualified_formal_dynamic_B/run_03/native_runtime.json)

Action状态4；未通过项：geometric_envelope_overlap_or_missing_samples。真值终点误差：位置0.0597m、朝向0.1122rad。最终实测速度[-1.981304289748012e-05, 1.3415582803960612e-09]；最小几何间距-0.0154m，重叠采样31；修复TF2实际加载核验True。

Action虽然成功，独立物理验收仍失败。停车后地图估计终点误差为0.0656m；它与世界真值是不同数据源，不能用估计合格替代真值合格，也不能为跨过门槛而四舍五入。

- `feasible_arc_collision_warning`：19条；首条原文：`[controller_server-8] [WARN] [1795325204.006404466] [controller_server]: AckermannRPP detected collision on feasible chassis arc`
- `planner_start_in_lethal_space`：1条；首条原文：`[planner_server-10] [WARN] [1795325204.416052293] [planner_server]: GridBased: failed to create plan, invalid use: Starting point in lethal space! Cannot create feasible plan..`

Action未到达仍计入成功率分母。目标被箱体覆盖属于预期不可达，需另核对停车与间距，不能计作避障到达。

## formal_dynamic_B / run_07

[原始结果](../results/20261122_132446_showcase_qualified_formal_dynamic_B/run_07/result.json) · [导航日志](../results/20261122_132446_showcase_qualified_formal_dynamic_B/run_07/navigation.log) · [原生TF2加载](../results/20261122_132446_showcase_qualified_formal_dynamic_B/run_07/native_runtime.json)

Action状态6；未通过项：navigation_action_status_6, world_position_error_exceeds_limit, world_heading_error_exceeds_limit。真值终点误差：位置2.5175m、朝向0.5688rad。最终实测速度[-3.8568233586767477e-07, 1.4300504693984292e-11]；最小几何间距0.1316m，重叠采样0；修复TF2实际加载核验True。

- `feasible_arc_collision_warning`：23条；首条原文：`[controller_server-8] [WARN] [1795325408.678677249] [controller_server]: AckermannRPP detected collision on feasible chassis arc`
- `planner_start_in_lethal_space`：10条；首条原文：`[planner_server-10] [WARN] [1795325409.767638922] [planner_server]: GridBased: failed to create plan, invalid use: Starting point in lethal space! Cannot create feasible plan..`
- `goal_failed`：1条；首条原文：`[bt_navigator-12] [ERROR] [1795325417.909736093] [bt_navigator]: Goal failed`

Action未到达仍计入成功率分母。目标被箱体覆盖属于预期不可达，需另核对停车与间距，不能计作避障到达。

## boundary_blocked_goal / run_01

[原始结果](../results/20261122_134854_showcase_fixed_blocked_goal_boundary/run_01/result.json) · [导航日志](../results/20261122_134854_showcase_fixed_blocked_goal_boundary/run_01/navigation.log) · [原生TF2加载](../results/20261122_134854_showcase_fixed_blocked_goal_boundary/run_01/native_runtime.json)

Action状态None；未通过项：simulation_timeout, world_position_error_exceeds_limit, world_heading_error_exceeds_limit。真值终点误差：位置1.2388m、朝向0.4181rad。最终实测速度[9.99614169654836e-05, -8.565028187001922e-10]；最小几何间距0.0996m，重叠采样0；修复TF2实际加载核验True。

- `feasible_arc_collision_warning`：418条；首条原文：`[controller_server-8] [WARN] [1795326581.327025629] [controller_server]: AckermannRPP detected collision on feasible chassis arc`
- `planner_start_in_lethal_space`：2条；首条原文：`[planner_server-10] [WARN] [1795326595.119307563] [planner_server]: GridBased: failed to create plan, invalid use: Starting point in lethal space! Cannot create feasible plan..`
- `tf_or_transform_warning`：3条；首条原文：`[bt_navigator-12] [ERROR] [1795326542.828677896] [transformPoseInTargetFrame]: Extrapolation Error looking up target frame: Lookup would require extrapolation into the past.  Requested time 6.794000 but the earliest data is at time 7.032000, when looking up transform from frame [base_footprint] to frame [map]`

Action未到达仍计入成功率分母。目标被箱体覆盖属于预期不可达，需另核对停车与间距，不能计作避障到达。

