# 最终批次失败逐例证据

这里只索引最终主对照和额外场景中的全部未到达记录；历史候选另在experiment_audit.json。日志计数是重复消息数，不是独立故障次数。模式匹配只描述观察，不替代根因证明。

## formal_dynamic_B / run_03

[原始结果](../results/20261121_032708_tf2q_formal_dynamic_B/run_03/result.json) · [导航日志](../results/20261121_032708_tf2q_formal_dynamic_B/run_03/navigation.log) · [原生TF2加载](../results/20261121_032708_tf2q_formal_dynamic_B/run_03/native_runtime.json)

Action状态6；未通过项：navigation_action_status_6, world_position_error_exceeds_limit, world_heading_error_exceeds_limit, insufficient_route_length。真值终点误差：位置6.5537m、朝向1.1878rad。最终实测速度[-5.8340214730590467e-05, -8.40055159343273e-08]；最小几何间距0.0294m，重叠采样0；修复TF2实际加载核验True。

- `feasible_arc_collision_warning`：15条；首条原文：`[controller_server-8] [WARN] [1795202931.963045503] [controller_server]: AckermannRPP detected collision on feasible chassis arc`
- `planner_start_in_lethal_space`：10条；首条原文：`[planner_server-10] [WARN] [1795202932.424993326] [planner_server]: GridBased: failed to create plan, invalid use: Starting point in lethal space! Cannot create feasible plan..`
- `tf_or_transform_warning`：3条；首条原文：`[bt_navigator-12] [ERROR] [1795202923.013455669] [transformPoseInTargetFrame]: Extrapolation Error looking up target frame: Lookup would require extrapolation into the past.  Requested time 6.484000 but the earliest data is at time 6.742000, when looking up transform from frame [base_footprint] to frame [map]`
- `goal_failed`：1条；首条原文：`[bt_navigator-12] [ERROR] [1795202940.666557470] [bt_navigator]: Goal failed`

Action未到达仍计入成功率分母。目标被箱体覆盖属于预期不可达，需另核对停车与间距，不能计作避障到达。

## boundary_blocked_goal / run_01

[原始结果](../results/20261121_035724_ak_final_boundary_blocked_goal/run_01/result.json) · [导航日志](../results/20261121_035724_ak_final_boundary_blocked_goal/run_01/navigation.log) · [原生TF2加载](../results/20261121_035724_ak_final_boundary_blocked_goal/run_01/native_runtime.json)

Action状态None；未通过项：simulation_timeout, world_position_error_exceeds_limit, world_heading_error_exceeds_limit。真值终点误差：位置1.0826m、朝向1.0092rad。最终实测速度[-6.220774604288851e-06, 7.196934296014937e-10]；最小几何间距0.1143m，重叠采样0；修复TF2实际加载核验True。

- `feasible_arc_collision_warning`：242条；首条原文：`[controller_server-8] [WARN] [1795204693.203329911] [controller_server]: AckermannRPP detected collision on feasible chassis arc`
- `tf_or_transform_warning`：3条；首条原文：`[bt_navigator-12] [ERROR] [1795204653.004483332] [transformPoseInTargetFrame]: Extrapolation Error looking up target frame: Lookup would require extrapolation into the past.  Requested time 6.904000 but the earliest data is at time 7.142000, when looking up transform from frame [base_footprint] to frame [map]`

Action未到达仍计入成功率分母。目标被箱体覆盖属于预期不可达，需另核对停车与间距，不能计作避障到达。

## boundary_close_front / run_01

[原始结果](../results/20261121_035905_ak_final_boundary_close_front/run_01/result.json) · [导航日志](../results/20261121_035905_ak_final_boundary_close_front/run_01/navigation.log) · [原生TF2加载](../results/20261121_035905_ak_final_boundary_close_front/run_01/native_runtime.json)

Action状态6；未通过项：navigation_action_status_6, world_position_error_exceeds_limit, world_heading_error_exceeds_limit, insufficient_route_length。真值终点误差：位置10.1386m、朝向1.6706rad。最终实测速度[0.0001325215762354736, -2.997545276252487e-07]；最小几何间距0.1314m，重叠采样0；修复TF2实际加载核验True。

- `feasible_arc_collision_warning`：478条；首条原文：`[controller_server-8] [WARN] [1795204758.479042463] [controller_server]: AckermannRPP detected collision on feasible chassis arc`
- `planner_start_in_lethal_space`：1条；首条原文：`[planner_server-10] [WARN] [1795204759.118604036] [planner_server]: GridBased: failed to create plan, invalid use: Starting point in lethal space! Cannot create feasible plan..`
- `goal_failed`：1条；首条原文：`[bt_navigator-12] [ERROR] [1795204793.377926931] [bt_navigator]: Goal failed`

Action未到达仍计入成功率分母。目标被箱体覆盖属于预期不可达，需另核对停车与间距，不能计作避障到达。

