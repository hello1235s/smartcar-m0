# M5-4：复盘、实验与基线包

```bash
source scripts/env.sh
.venv-ros/bin/python M5/M5-4/quick_review.py M5/runs/某次运行
.venv-ros/bin/python scripts/run_software_experiments.py
```

MCAP采用ROS2 std_msgs/String CDR编码，日志时间为墙钟ns，另存ros_ns。FSM事件与switch_log也用墙钟ns，不能直接减仿真时钟。复盘只解析白名单指标/故障/状态/切换/降级消息，不反序列化图像和点云；缺失指标保持不可用，损坏MCAP给出可读错误。自动选择前一把，可用--previous明确指定。首次实际复盘耗时约0.027秒，保留逐次实测耗时。

根因链只在fault stamp/topic构成的cause_id与处理事件明确关联时生成。单纯时间接近不当成因果。报告给出现象、实际处理、处理延迟；额外导航代价没有实测就写未测量。受控故障实验在Mock导航期间断开实际ROS模拟相机话题，验证自动暂停/降级标记、人工恢复后任务继续，相关MCAP和报告保留。

exp.py提供new/run/compare/promote。new只保存diff.yaml和元数据，运行时深合并；run热加载真实ONNX与实际参数，执行N场任务，逐场封存MCAP、FSM报告、切换和审计，记录Git提交与模型SHA256。默认演示两种模型、两种阈值共5场，明确是软件任务，不冒充实体抓取。compare输出Markdown表及自包含Plotly HTML。

promote只暂存指定基线和manifest两份文件；目标已有未提交修改或索引有无关文件时拒绝提交，保护M0已有改动。成功率以实际完成场数为分母，超时不从分母剔除。

package_baseline.py打包锁定参数、ONNX、样例图、预期输出、SHA256清单、运行时依赖及verify_baseline.sh/.py。自验要求无torch/tensorflow、形状[1,84,2100]、有限输出、CosSim>.99和所有文件哈希一致；不把这些阈值混写成赛道mAP或Orin性能。`results/cross_system/` 已在干净Ubuntu3.10与Windows3.11环境实际PASS。Windows中文路径使用imdecode+fromfile，重复打包不把manifest自身加入哈希。
