# UR5e Voice Grasp Workspace

这个工作区用于 UR5e 机械臂在 Gazebo 仿真中的语音抓取与固定区域放置实验。

当前主要能力：
- Gazebo 仿真中的红、绿、蓝三色方块场景
- 视觉检测与目标选择
- 语音输入后抓取指定颜色、最左边、最右边、第几个方块
- 语音输入后抓取并放到左侧 / 中间 / 右侧固定区域

## 工作区结构

核心原始功能包：
- [`src/ur_bringup`](/home/hw/arm-1/my_ws/src/ur_bringup): 仿真与抓取启动入口
- [`src/ur5e_gripper_moveit_config`](/home/hw/arm-1/my_ws/src/ur5e_gripper_moveit_config): MoveIt 与 Gazebo 场景
- [`src/ur5e_gripper_control`](/home/hw/arm-1/my_ws/src/ur5e_gripper_control): 原始抓取执行
- [`src/vision`](/home/hw/arm-1/my_ws/src/vision): 视觉检测、颜色解析、目标选择
- [`src/audio_record_pkg`](/home/hw/arm-1/my_ws/src/audio_record_pkg): 录音、Whisper ASR、语音对话能力

新增功能包：
- [`src/voice_grasp_bridge`](/home/hw/arm-1/my_ws/src/voice_grasp_bridge): 语音转抓取文本桥接
- [`src/voice_grasp_bringup`](/home/hw/arm-1/my_ws/src/voice_grasp_bringup): 语音桥接 + 安全抓取 wrapper
- [`src/voice_pick_bridge`](/home/hw/arm-1/my_ws/src/voice_pick_bridge): 面向“抓哪个”的语音抓取桥接
- [`src/voice_pick_place_bridge`](/home/hw/arm-1/my_ws/src/voice_pick_place_bridge): 面向“抓取并放置到固定区域”的语音桥接
- [`src/ur5e_pick_place_control`](/home/hw/arm-1/my_ws/src/ur5e_pick_place_control): 固定区域放置执行链

## 环境准备

建议先加载 ROS 2 和当前工作区：

```bash
cd /home/hw/arm-1/my_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
```

语音相关推荐使用工作区虚拟环境：

```bash
cd /home/hw/arm-1/my_ws
source .venv_whisper/bin/activate
```

常见依赖：
- `pyaudio`
- `openai-whisper`
- 可选：`opencc-python-reimplemented`
- 如果使用大模型解析：对应的 API Key 环境变量，例如 `DEEPSEEK_API_KEY`

## 构建

常用构建命令：

```bash
cd /home/hw/arm-1/my_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select \
  audio_record_pkg \
  vision \
  ur_bringup \
  voice_grasp_bridge \
  voice_grasp_bringup \
  voice_pick_bridge \
  voice_pick_place_bridge \
  ur5e_pick_place_control
source install/setup.bash
```

## Gazebo 场景

当前 Gazebo 场景文件：
[`src/ur5e_gripper_moveit_config/gazebo/sim_env.world`](/home/hw/arm-1/my_ws/src/ur5e_gripper_moveit_config/gazebo/sim_env.world)

当前场景默认保留：
- `red_box`
- `green_box`
- `blue_box`

如果你改了 world 文件但 Gazebo 没变化，先确保：
- 旧的 Gazebo 进程已经关闭
- 当前工作区里的 `install` 已经同步到最新内容
- 重新 `source install/setup.bash`

## 用法一：语音抓取

推荐三终端流程。

终端 1：启动仿真与视觉

```bash
cd /home/hw/arm-1/my_ws
source install/setup.bash
ros2 launch ur_bringup simulation.launch.py
```

终端 2：启动常驻抓取会话

```bash
cd /home/hw/arm-1/my_ws
source install/setup.bash
ros2 launch ur_bringup voice_triggered_grasp.launch.py
```

终端 3：启动语音抓取命令节点

规则版：

```bash
cd /home/hw/arm-1/my_ws
source install/setup.bash
ros2 run voice_pick_bridge voice_pick_command
```

LLM 版：

```bash
cd /home/hw/arm-1/my_ws
source install/setup.bash
ros2 run voice_pick_bridge voice_pick_llm_command
```

终端 3 交互方式：
- 输入 `R` 开始录音
- 输入 `S` 停止录音

常见示例：
- `抓红色方块`
- `抓最左边的方块`
- `抓最右边的蓝色方块`
- `抓第2个黄色方块`

## 用法二：语音抓取并放置到固定区域

推荐三终端流程。

终端 1：启动仿真与视觉

```bash
cd /home/hw/arm-1/my_ws
source install/setup.bash
ros2 launch ur_bringup simulation.launch.py
```

终端 2：启动常驻 pick-place 会话

```bash
cd /home/hw/arm-1/my_ws
source install/setup.bash
ros2 run voice_pick_place_bridge pick_place_session
```

终端 3：启动语音 pick-place 命令节点

```bash
cd /home/hw/arm-1/my_ws
source install/setup.bash
ros2 run voice_pick_place_bridge voice_pick_place_command
```

常见示例：
- `抓红色方块放到左侧区域`
- `抓最左边的方块放到中间区域`
- `抓蓝色方块放到右侧区域`

终端会打印：
- `ASR: ...`
- `REQ: {...}`

## 说明

交互式语音节点更推荐使用 `ros2 run`，而不是 `ros2 launch`。
原因是这些节点需要读取终端标准输入，`launch` 下对 `R/S/E` 这类交互支持不稳定。

## 相关文档

- [`src/audio_record_pkg/README.md`](/home/hw/arm-1/my_ws/src/audio_record_pkg/README.md)
- [`src/vision/README.md`](/home/hw/arm-1/my_ws/src/vision/README.md)
- [`src/voice_grasp_bridge/README.md`](/home/hw/arm-1/my_ws/src/voice_grasp_bridge/README.md)
- [`src/voice_grasp_bringup/README.md`](/home/hw/arm-1/my_ws/src/voice_grasp_bringup/README.md)
- [`src/voice_pick_bridge/README.md`](/home/hw/arm-1/my_ws/src/voice_pick_bridge/README.md)
- [`src/voice_pick_place_bridge/README.md`](/home/hw/arm-1/my_ws/src/voice_pick_place_bridge/README.md)
- [`src/ur5e_pick_place_control/README.md`](/home/hw/arm-1/my_ws/src/ur5e_pick_place_control/README.md)
