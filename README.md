# 智能车 M0 工程基础作业

作者：张驰。目标环境：Ubuntu 22.04.5 LTS、ROS 2 Humble、Python 3.10。

本项目按 M0-1～M0-4 保存代码、说明、测试和实际运行记录。
题目及原始示例来自 https://github.com/Blake-John/22SmartCar ，遵循 Apache-2.0 许可。
初始版本保存了尚未修复的教学脚本；后续提交逐步实现与验证。

AI 参与：Codex 协助环境检查、代码编写、测试和文档整理。每题的 AI 使用及验证情况会分别记录。
自动测试通过不代表作者已逐行理解；本人阅读和答辩准备需要单独完成。

| 目录 | 内容 |
| --- | --- |
| M0/M0-1 | 开发环境、真实踩坑记录与检查脚本 |
| M0/M0-2 | YAML/CSV 相关系数工具 |
| M0/M0-3 | 传感器数据清洗与缺陷报告 |
| M0/M0-4 | 依赖任务调度模拟器 |
| evidence | Ubuntu 实际运行证据 |

运行环境：

```bash
cd ~/smartcar-m0
export PATH="$HOME/.local/bin:$PATH"
uv venv --python /usr/bin/python3 --seed
uv pip install --python .venv/bin/python -r requirements-dev.txt
source .venv/bin/activate
```
