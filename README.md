# 智能车一轮作业：M1 与 M3

作者：张驰。个人作业仓库：<https://github.com/hello1235s/smartcar-m0>。

本分支 `codex/m1-m3-training` 提交 M1 四题和 M3 四题，沿用 M0 作业作为基础。实际环境为 Ubuntu 22.04、ROS 2 Humble、Gazebo Classic 11、VMware 6 vCPU。M1 使用题目合成传感器/图像数据，M3 使用 Gazebo 物理仿真；本次运行不依赖开发板、K230、麦克风或训练模型。

代码与历史实测证据来自开发提交 `2bf7fb0cf28bcbd60eb716e8020ac4865cff6a3e`，本分支按模块整理交付。原开发记录见 [开发分支](https://github.com/hello1235s/smartcar-m0/tree/codex/m1-m3-m5-m6)。历史证据日期为 2026-11-16；整理日期不能当成重新实验的日期。本次独立分支的检查另存 `evidence/M1-M3-submission/`。

**AI 使用：** Codex 参与 M1/M3 实现、调参、运行验证和文档整理。已执行的验证见下表及原始结果；作者本人逐行研究、独立复现和答辩准备程度尚待本人确认，不能用自动验收代替。完整披露见 [AI_USAGE.md](AI_USAGE.md)。

## 八道题与证据入口

| 任务 | 内容与历史实测 | 代码、说明和证据 |
|---|---|---|
| M1-1 | 三节点、自定义接口、动态滤波参数、服务超时；发布约10.01 Hz | [说明](M1/M1-1/README.md) · [链路记录](evidence/M1-chain/latest.json) |
| M1-2 | 双命名空间六节点、参数隔离、就绪探测和配置报错 | [说明](M1/M1-2/README.md) · [实际链路记录](evidence/M1-chain/) |
| M1-3 | TF、两组外参、同步扫参、投影图和仿真时钟切换录像 | [说明](M1/M1-3/README.md) · [结果](M1/M1-3/results/20261116_204426/) |
| M1-4 | 输出31.72 FPS、控制20.99 Hz、P95约26.71 ms；保留灰度增强语义 | [说明](M1/M1-4/README.md) · [踩坑记录](M1/M1-4/FAULTS.md) · [实测](M1/M1-4/results/) |
| M3-1 | 十次2m圆角闭环；odom位置误差0.2274±0.0411m，真值0.2843±0.0408m | [说明](M3/M3-1/README.md) · [20份CSV与图](M3/M3-1/results/20261116_210401/) |
| M3-2 | 自建环形场景、slam_toolbox地图、0.95m窄门；265节点/281边的实际图 | [说明](M3/M3-2/README.md) · [地图](M3/M3-2/maps/) · [图约束](M3/M3-2/results/replay_20261116_225310/graph_analysis.json) |
| M3-3 | AMCL与阿克曼Nav2；三次2成功/1超时，成功率66.7% | [说明](M3/M3-3/README.md) · [三次轨迹](M3/M3-3/results/20261116_220158_final_static/) |
| M3-4 | 动态注入障碍；A/B/B调优各10次，成功8/3/7次；失败边界与四指标 | [说明](M3/M3-4/README.md) · [分析](M3/M3-4/report.md) · [最终对照](M3/M3-4/results/matched_comparison/) |

数据口径、失败记录和限制见 [交付验收清单](docs/M1_M3_验收清单.md)。M3-4的主绕行指标是 `/plan` 规划长度估计，不是真值里程；M3-3的66.7%是三次试验的点估计，不保证任意现场都成功。

## 从干净的 Ubuntu 22.04 环境准备

先按 ROS 官方方法安装 ROS 2 Humble，并确认 `source /opt/ros/humble/setup.bash` 可用。以下是依赖安装和构建命令；已有依赖的环境可跳过安装。

```bash
sudo apt update
sudo apt install -y build-essential cmake git python3-venv python3-pip \
  python3-colcon-common-extensions python3-numpy python3-opencv python3-pyqt5 \
  libboost-serialization-dev libeigen3-dev nlohmann-json3-dev \
  ros-humble-desktop ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control \
  ros-humble-ros2-control ros-humble-ros2-controllers \
  ros-humble-ackermann-steering-controller ros-humble-navigation2 \
  ros-humble-nav2-bringup ros-humble-slam-toolbox ros-humble-tf2-tools \
  ros-humble-cv-bridge ros-humble-message-filters ros-humble-xacro
python3 -m venv --system-site-packages .venv-ros
.venv-ros/bin/python -m pip install -r requirements-m1-m3.txt
bash scripts/build_ros.sh
source scripts/env.sh
```

`--system-site-packages` 用于复用 apt 安装的 ROS、cv_bridge 和 PyQt5。不要把 NumPy 升为2.x；不要用其他模型训练环境覆盖 ROS 的 Python 路径。脚本只构建 `sensor_interfaces`、`smartcar_training`、`smart_car_description` 三个包。

## 运行与复现

以下命令从仓库根目录执行。多终端运行时每个终端都先 `source scripts/env.sh`；Gazebo/投影窗口需要已登录的 Ubuntu 图形桌面。仿真批次应依次运行，避免抢占 Gazebo 端口和资源。

```bash
# M1-1/2：链路、动态参数、命名空间与超时检查
.venv-ros/bin/python scripts/verify_m1_chain.py
# M1-3：生成两组bag并回放，输出投影和时钟证据
.venv-ros/bin/python scripts/verify_projection.py
# M1-4：检查处理语义，再运行性能对照
.venv-ros/bin/python M1/M1-4/semantic_check.py
.venv-ros/bin/python M1/M1-4/measure_chain.py --seconds 24
# M3-1：十次方形闭环
.venv-ros/bin/python scripts/verify_square.py
# M3-2：重新巡场、建图和保存bag
.venv-ros/bin/python scripts/verify_mapping.py
# M3-3：一条命令起Gazebo、地图、定位和导航
ros2 launch ./M3/M3-3/bringup.launch.py
# 或用批量脚本自行启动/关闭三次导航，勿与上一条同时运行
.venv-ros/bin/python scripts/verify_navigation.py --runs 3
# M3-4：三组各10次动态障碍试验
.venv-ros/bin/python M3/M3-4/scripts/run_benchmark.py --runs 10
```

完整建图和30次导航复测耗时较长；Git保留原始CSV/JSON、地图、图表和失败样本。大型rosbag不在Git内：合成bag可重新生成，实测建图bag可执行 `verify_mapping.py` 重新采集，既有原始bag仍保留在原Ubuntu工作目录及先前本地交付包。

## 本人学习与现场验收

[答辩准备](docs/M1_M3_答辩准备.md) 是阅读和练习清单，不代表作者已掌握。现场前需本人独立运行、修改参数并解释结果。此前的M0说明可在 [M0目录](M0/) 查看；本分支没有继续提交M5/M6任务。

来源与依赖见 [THIRD_PARTY.md](THIRD_PARTY.md)。
