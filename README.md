# UR5e 智能抓取系统

一个基于 ROS 2 Humble + MoveIt 2 + Gazebo + RGB-D 视觉的 UR5e 抓取项目，支持从目标检测到抓取执行的完整闭环流程。

## 功能概览

- UR5e + Robotiq 夹爪仿真控制
- MoveIt2 运动规划与执行
- RGB-D 目标检测与三维定位
- 方块目标 TF 发布（`cube1...cubeN`）
- 文字指令选目标（`openai_selector`）
- 腕部相机目标朝向估计与抓取角度微调
- 自动抓取与放置流程

## 目录结构

`my_ws/src` 主要包：

- `ur_bringup`：系统启动入口
- `ur5e_gripper_moveit_config`：MoveIt 与仿真配置
- `ur5e_gripper_control`：抓取执行节点
- `ur5e_gripper_description`：UR5e+夹爪描述
- `robotiq_description`：夹爪描述
- `robotiq_moveit_config`：夹爪 MoveIt 配置
- `vision`：检测、定位、目标选择、腕部朝向估计
- `sim_models/*`：Gazebo/RealSense 相关模型与插件

## 环境要求

- Ubuntu 22.04
- ROS 2 Humble
- MoveIt2（Humble）
- Gazebo（ROS2 版本）
- Python 3.10+

建议依赖安装：

```bash
sudo apt update
sudo apt install ros-humble-desktop ros-humble-moveit-*
sudo apt install ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control
sudo apt install ros-humble-vision-msgs ros-humble-cv-bridge ros-humble-image-transport
pip install ultralytics
```

## 编译

```bash
cd /home/hw/my_project/my_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## 快速开始

### 1) 启动仿真 + MoveIt + 视觉链路

```bash
cd /home/hw/my_project/my_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur_bringup simulation.launch.py
```

### 2) 启动抓取流程

新开一个终端：

```bash
cd /home/hw/my_project/my_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur_bringup start_grasp.launch.py
```

## 常用命令

1. 指定抓取目标

```bash
ros2 launch ur_bringup start_grasp.launch.py \
  target_cube_frame:=cube3 \
  grasp_all_if_no_target:=false
```

2. 文字指令触发目标选择

```bash
ros2 launch ur_bringup start_grasp.launch.py \
  grasp_command_text:="抓最左边红色方块"
```

3. 开启朝向估计调试图

```bash
ros2 launch ur_bringup simulation.launch.py \
  enable_wrist_yaw_estimator:=true \
  wrist_yaw_target_color:=all \
  wrist_yaw_publish_debug_image:=true
```

## 关键话题

- `/detection`：检测结果
- `/grasp_target_frame`：目标方块帧名
- `/grasp_command_text`：抓取文字指令
- `/wrist_target_yaw`：腕部目标朝向（绝对）
- `/wrist_target_yaw_delta`：腕部目标朝向（增量）
- `/wrist_yaw_debug_image`：腕部朝向调试图

## 常见问题

### 1. 抓取时朝向没有生效

检查是否有朝向数据发布：

```bash
ros2 topic hz /wrist_target_yaw_delta
ros2 topic echo /wrist_target_yaw_delta --once
```

并确认：

- `simulation.launch.py` 中 `enable_wrist_yaw_estimator:=true`
- `start_grasp.launch.py` 中 `enable_wrist_yaw_refine:=true`

### 2. 检测不到目标

确认模型文件存在：

`/home/hw/my_project/my_ws/src/vision/vision/yolov11/models/best.pt`

### 3. launch 报日志目录权限问题

```bash
export ROS_LOG_DIR=/tmp/ros_logs
```

## 可选配置

如需使用 LLM 目标解析：

```bash
export OPENAI_API_KEY=your_api_key
```

未配置时会自动使用规则匹配模式。
