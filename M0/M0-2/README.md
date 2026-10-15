# M0-2：相关系数工具

入口为 `corr_tool.py`；`legacy_corr.py` 保留题目原始代码，便于对照缺陷，不作为作业运行入口。

**运行**

在项目根目录激活虚拟环境后执行：

```bash
python M0/M0-2/corr_tool.py --config M0/M0-2/config.yaml
python -m pytest M0/M0-2/tests -q
```

也可进入本目录执行 `python corr_tool.py --config config.yaml`。
YAML 顶层字段 `input_csv` 是 CSV 路径，`columns.x` 和 `columns.y` 是待计算列名。
CSV 相对路径始终相对于配置文件所在目录；配置文件本身的相对路径相对于当前工作目录。
允许额外列，计算只读取指定两列；UTF-8 BOM 可正常读取。

```yaml
input_csv: sample_data.csv
columns:
  x: sensor_a
  y: sensor_b
task:
  name: corr_analysis
  verbose: true
```

`task` 为样例的说明字段，本程序不依赖该字段，始终输出样本数、两列均值及 r，方便现场验收。
至少需要两条有限数值数据。拒绝缺列、重复表头、行列数不符、空值、非数值、NaN、Infinity、零方差。
文件不存在、无权限、空文件、配置损坏等错误输出至 stderr，退出码为 2，不暴露 Python 栈回溯。
成功退出码为 0，stdout 包含 `r = <数值>`。

**公式与结果**

先对两列减去各自均值。Pearson r 的分子是中心化向量的点积，分母是两个向量长度的乘积。
原脚本漏了分母中的平方根，因此正比例序列也不一定得到 1。
修复后使用 `math.fsum` 累加、`math.hypot` 计算向量长度，再对归一化乘积求和，避免原平方和乘积溢出。
不调用 NumPy 或 SciPy 实现核心公式；NumPy 仅在测试中作独立对照。

随题样例的实际输出：

```text
n = 40
mean_x = 49.437825
mean_y = 43.310725
r = 0.563474725452
```

`n` 为有效成对样本数量；`mean_x`、`mean_y` 为原数据均值。
r 在 [-1,1] 之间，正数表示同向线性关系，负数表示反向线性关系，接近 0 表示线性关系弱。
相关性不证明因果关系；某列方差为零时 r 无定义。

**开发与验证记录**

Git 依次记录函数拆分、公式修复、异常校验、命令行测试及文档五次独立改动。
`evidence/m02_formula_before.log` 是修复前真实测试记录，3 项失败；修复后公式用例全部通过。
最终 28 项测试涵盖正负相关、零相关、独立随机数据、错误输入、新路径调用、无副作用导入及大数。
现场新数据尚未收到，不能声称已通过正式考核。

**AI 使用与个人学习**

Codex 编写重构代码、测试和本说明，实际连接 Ubuntu 运行验证，并记录 Git 提交。
本人是否已经逐行理解：待张驰本人阅读后确认。答辩前需解释分母平方根、零方差、路径解析与错误退出。

题目来源：https://github.com/Blake-John/22SmartCar/tree/main/round1/M0/M0-2
