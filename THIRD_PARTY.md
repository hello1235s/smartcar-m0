# M1/M3 来源与环境

- 题目、原始合成数据脚本、故意低效的图像脚本及车辆模型来自 [Blake-John/22SmartCar](https://github.com/Blake-John/22SmartCar)，源提交 `cdc8dd45296f4eaf57924c0686d861e07252905d`。原仓库许可证 Apache-2.0，沿用基础作业中的LICENSE；原始车辆/配置副本以original等名称保留。
- M1-3 `make_bag.py` 为题目提供的生成器；M1-4 `baseline/` 为原版性能基线。生成数据和仿真不能称为实际道路传感器采集。
- 目标环境：Ubuntu 22.04、ROS2 Humble、Gazebo Classic 11；实际使用 `ackermann_steering_controller` 2.54.0。轮对顺序修正是针对该版本的适配，现场换版本应重新核查接口。
- ROS组件：rclpy、tf2_ros、message_filters、cv_bridge、slam_toolbox、Nav2、ros2_control、gazebo_ros、robot_state_publisher、xacro、tf2_tools。
- Python统计/绘图使用NumPy 1.23.5、matplotlib 3.7.5、pandas 1.5.3、PyYAML；OpenCV和PyQt5来自Ubuntu系统包，使用system-site-packages虚拟环境。
- 序列化位姿图分析工具使用slam_toolbox提供的karto SDK、Boost serialization、Eigen和rclcpp。构建命令见M3-2说明。
- 自有代码与文档的AI参与范围及本人研究状态见 [AI_USAGE.md](AI_USAGE.md)。
