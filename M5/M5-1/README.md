# M5-1：纯 Python 任务内核

```bash
source scripts/env.sh
.venv-ros/bin/python -m pytest -q M5/M5-1/tests
.venv-ros/bin/python M5/M5-1/run_task.py M5/M5-1/tasks/task_demo.yaml --backend mock --out M5/task_report.json
```

core.py约157行非空代码，包含YAML校验、建节点、超时、并行、重试、fallback和回跳，未使用现成行为树库。六种节点状态为IDLE/RUNNING/SUCCESS/FAILED/SKIPPED/RETRYING。TaskContext保存任务ID、单调时钟截止时间、共享数据、全局重试预算、降级标记和元数据。

每步retry同时受全局预算20约束；fallback允许回跳，但每个节点最多访问3次，并受任务总截止时间约束。Parallel配置为 `parallel: {branches: [...], fail_policy: any_fail|all_must_succeed}`：任一失败立即协作取消，或收集完所有分支结果。YAML中任务名必须唯一，type/fallback/timeout/retry等先校验，未知类型及YAML语法错误给出可读说明。

五个标准节点接口严格统一：setup/execute/cancel/teardown；execute返回SUCCESS/FAILED/SKIPPED。每节点有正常、超时、重试、取消测试；另测回跳预算、并行策略、全局截止时间、暂停/继续、跳过和abort，共30个契约测试。取消使用Event协作完成；0.5秒内不响应取消的扩展节点会被明确判为契约错误，而不是遗留后台任务。

任务顺序只在tasks/task_demo.yaml中。NavigateTo支持pose或pose_from_context；DetectTarget按类别和置信度写target_pose/id；ExecuteGrasp从上下文取位姿；SpeakTTS使用text。事件包含墙钟ts_ns、task_id、节点名、状态和耗时，GUI通过ROS镜像同一份事件，不另造状态。

默认MockBackend明确标记mock=true，不能据此声称实车导航/抓取。`--backend ros` 连接NavigateToPose、/perception/targets、/manipulation/grasp和/tts/speak；自定义Grasp和SpeakTTS接口在sensor_interfaces中。ROS目标接受与取消竞态有晚到取消兜底。机械臂和真实抓取硬件不在当前设备清单内，相关实物验证保留待补。
