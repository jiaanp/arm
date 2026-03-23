# voice_grasp_bridge

一个独立的 ROS 2 Python 包，用于把语音指令转成文字并发布到 `/grasp_command_text`。

这个包不会修改现有工程中的任何文件，只新增一个桥接节点：

- 录音
- Whisper 识别
- 发布抓取文字指令

示例：

- `抓红色方块`
- `抓最左边的蓝色方块`
- `抓第2个黄色方块`

运行方式：

1. 先启动你现有的仿真和抓取链路
2. 单独启动这个节点

```bash
cd /home/hw/arm-1/my_ws
colcon build --packages-select voice_grasp_bridge
source install/setup.bash
ros2 run voice_grasp_bridge voice_grasp_command
```

也可以通过 launch 启动：

```bash
ros2 launch voice_grasp_bridge voice_grasp_command.launch.py
```

终端交互：

- 输入 `R` 开始录音
- 输入 `S` 停止录音并识别

依赖说明：

- `pyaudio`
- `openai-whisper`
- 可选：`opencc-python-reimplemented`

如果工作区里存在 `.venv_whisper/bin/python3`，节点会自动切换到该 Python 解释器运行。
