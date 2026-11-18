# 智能车 M0 工程基础作业

作者：张驰。目标环境：Ubuntu 22.04.5 LTS、ROS 2 Humble、Python 3.10。

本项目按 M0-1～M0-4 保存代码、说明、测试和实际运行记录。
题目及原始示例来自 https://github.com/Blake-John/22SmartCar ，遵循 Apache-2.0 许可。
初始版本保存了尚未修复的教学脚本；后续提交逐步实现与验证。当前三道编程题已在 Ubuntu 中完成自测。

AI 参与：Codex 协助环境检查、代码编写、测试和文档整理。每题的 AI 使用及验证情况会分别记录。
自动测试通过不代表作者已逐行理解；本人阅读和答辩准备需要单独完成。

| 目录 | 内容 |
| --- | --- |
| M0/M0-1 | 开发环境、真实踩坑记录与检查脚本 |
| M0/M0-2 | YAML/CSV 相关系数工具 |
| M0/M0-3 | 传感器数据清洗与缺陷报告 |
| M0/M0-4 | 依赖任务调度模拟器 |
| evidence | Ubuntu 实际运行证据 |

| 检查 | 结果 |
| --- | --- |
| M0-1 环境验收 | PASS=32、FAIL=0、WARN=0 |
| M0-2 | 28 项测试通过 |
| M0-3 | 17 项测试通过，60 条样例保留 57 条 |
| M0-4 | 41 项测试通过，正常/重试跳过/中途超时演示完成 |
| 总计 | 86 项测试全部通过 |

完整记录见 `验收记录.md`，个人阅读提示见 `答辩准备.md`。
尚待本人阅读答辩、独立开发板远程演示和正式现场新数据验收。

运行环境：

```bash
cd ~/smartcar-m0
export PATH="$HOME/.local/bin:$PATH"
uv venv --python /usr/bin/python3 --seed
uv pip install --python .venv/bin/python -r requirements-lock.txt
source .venv/bin/activate
bash scripts/run_acceptance.sh
```

云端仓库：https://github.com/hello1235s/smartcar-m0

分支：`codex/m0-training`。主工作目录：Ubuntu 的 `~/smartcar-m0`。
`requirements-lock.txt` 固定实际通过测试的完整依赖；`requirements-dev.txt` 描述开发依赖范围。
运行依赖仅 PyYAML，NumPy 与 pytest 用于独立对照和测试。

本虚拟机 hosts 将 github.com 指向本机，因此 origin 使用 GitHub 官方 `ssh.github.com:443` 入口。
仓库 SSH 配置指定本机用户密钥和官方服务器公钥；私钥不在仓库中。
