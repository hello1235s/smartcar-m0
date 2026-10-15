# M0-4：TaskScheduler 任务调度模拟器

`scheduler.py` 是纯 Python 终端程序。Python 3.10 及以上可用，运行依赖仅 PyYAML。
使用项目根目录的 uv 虚拟环境；独立运行时也可在本题目录创建虚拟环境并安装 `requirements.txt`。

**运行示例**

在项目根目录 `source .venv/bin/activate` 后运行：

```bash
# 1. YAML 样例，固定种子，一般流程。
python M0/M0-4/scheduler.py --config M0/M0-4/tasks_demo.yaml --timeout 15 --report report.json --seed 42

# 2. 同一套任务读取 JSON，报告保存为 YAML。
python M0/M0-4/scheduler.py --config M0/M0-4/tasks_demo.json --timeout 15 --report report.yaml --seed 7

# 3. 明确演示首次失败、两次重试、下游跳过与独立分支继续。
python M0/M0-4/scheduler.py --config M0/M0-4/tasks_failure.yaml --report failure_report.json --seed 42

# 4. 20 秒长任务在约 0.2 秒时被全局超时中断。
python M0/M0-4/scheduler.py --config M0/M0-4/tasks_timeout.yaml --report timeout_report.json

# 5. 自动测试。
python -m pytest M0/M0-4/tests -q
```

失败分支示例退出码 1、超时示例退出码 124，都是预期演示结果。
`M0/M0-4/report.json` 保存了随题正常样例在 Ubuntu 中的真实运行结果。

| 参数 | 含义 |
| --- | --- |
| `--config` | 必填；YAML、YML 或 JSON 配置路径 |
| `--timeout` | 可选正数，覆盖配置中的 timeout；均未指定时为 15 秒 |
| `--report` | 输出报告路径；默认当前工作目录的 report.json；支持 JSON/YAML |
| `--seed` | 固定局部随机数生成器种子，重现成功/失败序列 |
| `--color` | auto/always/never；交互终端自动彩色，重定向默认去掉 ANSI |

文件路径均相对于当前工作目录。报告父目录需事先存在；禁止将报告写到输入配置本身。
样例任务为 5～8 个，程序也接受其他正数任务数量，便于独立测试最小依赖图。

**调度规则**

先完整验证输入，再使用 Kahn 拓扑排序；独立分支按输入顺序稳定入队。
支持分叉与汇合，检测环、缺失依赖、重复名称及重复依赖。总时间复杂度为 O(V+E)。
任务 duration 为非负有限数值；success_rate 为 [0,1] 的有限数值，不接受布尔值代替数值。

每次尝试使用真实 sleep 模拟耗时；随机数小于 success_rate 代表成功。
任务最多尝试 3 次；重试耗尽的最终状态为 SKIPPED，并导致所有受影响下游跳过，独立分支继续。
FAILED 是单次尝试失败日志，RETRY 是重试日志；两者不等同于最终任务被跳过。
绿色 SUCCESS、红色 FAILED、黄色 RETRY、蓝色 SKIPPED；TIMEOUT 用红色显示。

超时采用 `time.monotonic()`，避免系统时钟调整影响预算；单次 sleep 最长等于剩余预算。
这可以在 20 秒任务执行中于 0.2 秒预算处停止，而不是睡满 20 秒才报告超时。
时间精度受操作系统调度影响，因此实测会比预算多出少量调度开销，不能声称硬实时。
超时后保留已完成任务状态，正在执行及尚未执行的任务均标记 TIMEOUT。

**报告格式与退出码**

报告包含 `timeout` 布尔值、`total_duration` 总耗时、`timeout_seconds` 预算、种子、实际开始过的任务顺序及 tasks。
tasks 按原配置顺序列出每个任务，包含 name、status、attempts、duration、started_at、ended_at、reason。
attempts 不超过 3；duration 累计该任务所有尝试实际消耗的秒数；总耗时包含调度与日志开销。
起止时间为 Unix 秒时间戳；从未开始的任务时间为 null，尝试次数和耗时为 0。
每个配置任务都出现在报告中，包括依赖跳过和超时未执行的任务。

| 退出码 | 含义 |
| --- | --- |
| 0 | 全部任务成功 |
| 1 | 没有全局超时，但存在失败重试耗尽或依赖跳过 |
| 2 | 配置、命令参数或文件读写错误，输出可读错误，无栈回溯 |
| 124 | 全局超时，仍生成包含全部任务的报告 |

**验证与 AI 使用**

41 项测试覆盖配置、拓扑排序、菱形依赖、失败传播、第三次尝试成功、零耗时、固定种子、真实超时、
YAML 报告、强制颜色、错误输入和输入文件保护。可控时钟用于精确检查状态，另有真实子进程计时验证。
各演示日志和报告保存在 evidence；现场新配置仍需正式验收。

Codex 编写代码、测试和本说明，连接 Ubuntu 实际验证并提交 Git。
张驰本人逐行理解情况待确认；答辩需解释拓扑排序、失败传播、三次尝试与单调时钟。

题目来源：https://github.com/Blake-John/22SmartCar/tree/main/round1/M0/M0-4
