# M1-2 参数文件、命名空间与启动就绪

从仓库根目录 source `scripts/env.sh`，在两个终端使用同一个 Launch：

```bash
ros2 launch smartcar_training bringup.launch.py namespace:=robot1
ros2 launch smartcar_training bringup.launch.py namespace:=robot2 params_file:=$SMARTCAR_ROOT/M1/M1-2/params_robot2.yaml
ros2 param get /robot1/node_c_alarm alarm_threshold
ros2 param get /robot2/node_c_alarm alarm_threshold
ros2 launch smartcar_training bringup.launch.py params_file:=/nope.yaml
```

支持 `namespace`（robot1）、`params_file`（空时使用包内 robot1 文件）、`use_sim_time`（false）。两套 YAML 通过 `/**/node_*` 匹配完整节点名；robot1 阈值为 0.3，robot2 为 0.5。所有话题、服务均随命名空间隔离。

启动顺序：B 进程启动 → 临时 readiness 探针调用 B 的 GetParameters 服务并收到 alpha → 探针成功退出 → 启动 C。这样验证的是 B 已进入执行器并能响应请求，而不只是进程已创建。探针失败会清晰退出，不启动 C；正常运行仅有六个业务节点。

已实际验收六个节点、两组阈值和话题隔离。缺失 YAML 输出 `[ERROR] Parameter YAML file does not exist: /nope.yaml`，没有 Python 栈回溯。验收脚本与日志同 M1-1。

Humble 兼容记录：当前安装版本不导出 `launch.actions.LogError`，初次 Launch 因 ImportError 失败；已改为 `LogInfo` 输出明确 ERROR 前缀，原始失败日志保留在 `evidence/M1-chain/`。实际安装的 Launch 位于 M1-1 包内，本目录保留同内容交付副本。

## AI参与与本人研究状态

本题由Codex协助代码/配置、实验验证及文档整理；已有实测证据见本页。本人逐行研究和独立复现程度尚未确认，待本人学习后更新。详细范围见[AI使用说明](../../AI_USAGE.md)，现场要求见[验收清单](../../docs/M1_M3_验收清单.md)。自动验证不替代本人理解或考官验收。

## 本轮完整复测

本轮已重新执行题面检查，任务内容、逐项结果和原始总报告见[完整验收](../ACCEPTANCE.md)。历史测量保留原日期，不冒充本轮成绩。
