# 智能车一轮作业：M1 与 M3

作者：张驰。个人作业仓库：<https://github.com/hello1235s/smartcar-m0>。

本分支 `codex/m1-m3-training` 提交 M1 四题和 M3 四题，沿用 M0 作业作为基础。实际环境为 Ubuntu 22.04、ROS 2 Humble、Gazebo Classic 11、VMware 6 vCPU。M1 使用题目合成传感器/图像数据，M3 使用 Gazebo 物理仿真；本次运行不依赖开发板、K230、麦克风或训练模型。

M1代码与历史测量来自开发提交2bf7fb0，保留2026-11-16的测量日期。M3本轮在2026-11-21继续优化并实际重新采集；旧M3记录单独保留，当前结论以M3/optimization/REPORT.md为准。本分支新增验证记录可从evidence/和验收索引追溯，整理日期不代替实验日期。

**AI 使用：** Codex 参与 M1/M3 实现、调参、运行验证和文档整理。已执行的验证见下表及原始结果；作者本人逐行研究、独立复现和答辩准备程度尚待本人确认，不能用自动验收代替。完整披露见 [AI_USAGE.md](AI_USAGE.md)。

## 八道题与证据入口

| 任务 | 内容与实测（日期见来源） | 代码、说明和证据 |
|---|---|---|
| M1-1 | 三节点、自定义接口、动态滤波参数、服务超时；发布约10.01 Hz | [说明](M1/M1-1/README.md) · [链路记录](evidence/M1-chain/latest.json) |
| M1-2 | 双命名空间六节点、参数隔离、就绪探测和配置报错 | [说明](M1/M1-2/README.md) · [实际链路记录](evidence/M1-chain/) |
| M1-3 | TF、两组外参、同步扫参、投影图和仿真时钟切换录像 | [说明](M1/M1-3/README.md) · [结果](M1/M1-3/results/20261116_204426/) |
| M1-4 | 输出31.72 FPS、控制20.99 Hz、P95约26.71 ms；保留灰度增强语义 | [说明](M1/M1-4/README.md) · [踩坑记录](M1/M1-4/FAULTS.md) · [实测](M1/M1-4/results/) |
| M3-1 | odom反馈十次；真值闭合0.0183±0.0054m、1.64±0.19° | [说明](M3/M3-1/README.md) · [优化实测](M3/optimization/REPORT.md) |
| M3-2 | 后轴TF修正后真实重建SLAM；0.95m门，268节点/284边/17历史约束 | [说明](M3/M3-2/README.md) · [地图与来源](M3/M3-2/maps/) |
| M3-3 | AMCL、阿克曼Nav2、有效位姿检查；严格10/10 | [说明](M3/M3-3/README.md) · [全部成败](M3/optimization/report/all_attempts.csv) |
| M3-4 | 动态实体障碍，A/B/B_tuned各10次：10/9/9次通过；另有独立位置/目标与边界 | [说明](M3/M3-4/README.md) · [分析](M3/M3-4/report.md) · [当前对照](M3/optimization/report/) |

当前M3使用严格真值终点验收与实际轨迹积分，见[优化总报告](M3/optimization/REPORT.md)；旧66.7%、8/3/7等成绩保留为历史，不能与新口径直接混算。验收边界见[清单](docs/M1_M3_验收清单.md)。

## 从干净的 Ubuntu 22.04 环境准备

先按 ROS 官方方法安装 ROS 2 Humble，并确认 `source /opt/ros/humble/setup.bash` 可用。以下是依赖安装和构建命令；已有依赖的环境可跳过安装。

```bash
sudo apt update
sudo apt install -y build-essential cmake git python3-venv python3-pip \
  python3-colcon-common-extensions python3-numpy python3-opencv python3-pyqt5 \
  libboost-serialization-dev libeigen3-dev libtbb-dev nlohmann-json3-dev \
  ros-humble-desktop ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control \
  ros-humble-ros2-control ros-humble-ros2-controllers \
  ros-humble-ackermann-steering-controller ros-humble-navigation2 \
  ros-humble-nav2-bringup ros-humble-slam-toolbox ros-humble-tf2-tools \
  ros-humble-cv-bridge ros-humble-message-filters ros-humble-xacro
python3 -m venv --system-site-packages .venv-ros
.venv-ros/bin/python -m pip install -r requirements-m1-m3.txt
bash scripts/build_ros.sh
bash scripts/install_m3_runtime.sh
source scripts/env.sh
```

`--system-site-packages` 用于复用 apt 安装的 ROS、cv_bridge 和 PyQt5。不要把 NumPy 升为2.x；不要用其他模型训练环境覆盖 ROS 的 Python 路径。脚本只构建 `sensor_interfaces`、`smartcar_training`、`smart_car_description`、`smartcar_nav_checks` 四个包。

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
source scripts/m3_nav_env.sh
ros2 launch ./M3/M3-3/bringup.launch.py
# 或用批量脚本自行启动/关闭三次导航，勿与上一条同时运行
.venv-ros/bin/python scripts/verify_navigation.py --runs 3
# M3-4：三组各10次动态障碍试验
.venv-ros/bin/python M3/M3-4/scripts/run_benchmark.py --runs 10
```

完整建图和30次导航复测耗时较长；Git保留原始CSV/JSON、地图、图表和失败样本。大型rosbag不在Git内：合成bag可重新生成，实测建图bag可执行 `verify_mapping.py` 重新采集，既有原始bag仍保留在原Ubuntu工作目录及先前本地交付包。

## 本人学习与现场验收

个人学习材料单独保存在本地。现场前需本人独立运行、修改参数并解释结果。此前的M0说明可在 [M0目录](M0/) 查看；本分支没有继续提交M5/M6任务。

来源与依赖见 [THIRD_PARTY.md](THIRD_PARTY.md)。

## M3本轮更新

实现与实测已更新；M1原实现保留，并执行共享环境回归。当前代码、地图、配置、实验结果、图表和复现入口见[优化总报告](M3/optimization/REPORT.md)，每条题面要求对应[逐项证据索引](M3/optimization/acceptance_matrix.md)。答辩材料与PDF只在本地。
