# M1/M3 来源与环境

- 题目、原始合成数据脚本、故意低效的图像脚本及车辆模型来自 [Blake-John/22SmartCar](https://github.com/Blake-John/22SmartCar)，源提交 `cdc8dd45296f4eaf57924c0686d861e07252905d`。原仓库许可证 Apache-2.0，沿用基础作业中的LICENSE；原始车辆/配置副本以original等名称保留。
- M1-3 `make_bag.py` 为题目提供的生成器；M1-4 `baseline/` 为原版性能基线。生成数据和仿真不能称为实际道路传感器采集。
- 目标环境：Ubuntu 22.04、ROS2 Humble、Gazebo Classic 11；实际使用 `ackermann_steering_controller` 2.54.0。轮对顺序修正是针对该版本的适配，现场换版本应重新核查接口。
- ROS组件：rclpy、tf2_ros、message_filters、cv_bridge、slam_toolbox、Nav2、ros2_control、gazebo_ros、robot_state_publisher、xacro、tf2_tools。
- Python统计/绘图使用NumPy 1.23.5、matplotlib 3.7.5、pandas 1.5.3、PyYAML；OpenCV和PyQt5来自Ubuntu系统包，使用system-site-packages虚拟环境。
- 序列化位姿图分析工具使用slam_toolbox提供的karto SDK、Boost serialization、Eigen、TBB和rclcpp。独立构建时显式链接TBB，避免仅依赖间接库导致DSO missing；构建命令见M3-2说明。
- 自有代码与文档的AI参与范围及本人研究状态见 [AI_USAGE.md](AI_USAGE.md)。

本轮增加本仓库C++插件smartcar_nav_checks（Apache-2.0），使用Nav2 GoalChecker和RPP公开/受保护接口；未修改apt安装的Nav2二进制。后轴运动学、Humble目标转换失败链路及通信配置的官方链接见M3/optimization/REPORT.md。

M3导航的本地依赖来自官方ROS apt软件包：[CycloneDDS 0.10.5](https://github.com/eclipse-cyclonedds/cyclonedds/tree/0.10.5)（EPL-2.0或EDL-1.0）、[rmw_cyclonedds](https://github.com/ros2/rmw_cyclonedds/tree/humble)（Apache-2.0）、[iceoryx 2.0.5](https://github.com/eclipse-iceoryx/iceoryx/tree/v2.0.5)（Apache-2.0）、[TF2 core0.25.24](https://github.com/ros2/geometry2/tree/0.25.24/tf2)（BSD，官方锁顺序修复见geometry2 PR990）。版本锁在M3/runtime/navigation-packages.lock；实际包版本和SHA256随实验dds_packages文件保存。未修改这些依赖；Git只提交安装脚本/配置，离线包保留原.deb及其中的版权材料。


## 最新指南补齐

最新展示要求另参考教师仓库dbfd7cf6cbfaec4380e7f5a24654e38c24292732。原生RViz窗口使用ROS官方rviz_common::VisualizationFrame、rviz_rendering::RenderWindow及其插件，不以自绘图替代RViz；运行另需qtbase5-dev、ros-humble-rviz-common、ros-humble-rviz-rendering。 结果索引：[工程验收](docs/showcase_acceptance.md)。
