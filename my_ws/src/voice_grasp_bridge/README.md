# voice_grasp_bridge

独立的 ROS 2 语音桥接包，用于把语音指令转成抓取文本并发布到 ROS topic。

主要节点：
- `voice_grasp_command`: 录音 + Whisper ASR + 直接发布抓取文本
- `voice_llm_command`: 录音 + Whisper ASR + 大模型整理抓取文本

默认相关 topic：
- 早期桥接可发到 `/grasp_command_text`
- 当前会话式抓取流程更常配合 `/voice_grasp_request`

## 功能

- 录音保存为 `wav`
- Whisper 识别中文语音
- 可选使用大模型整理抓取命令
- 输出抓取文本到 ROS topic

示例命令：
- `抓红色方块`
- `抓最左边的蓝色方块`
- `抓第2个黄色方块`

## 构建

```bash
cd /home/hw/arm-1/my_ws
colcon build --packages-select voice_grasp_bridge
source install/setup.bash
```

## 运行

推荐直接运行交互节点：

```bash
ros2 run voice_grasp_bridge voice_grasp_command
```

或 LLM 版本：

```bash
ros2 run voice_grasp_bridge voice_llm_command
```

也可以通过 launch 启动：

```bash
ros2 launch voice_grasp_bridge voice_grasp_command.launch.py
ros2 launch voice_grasp_bridge voice_llm_command.launch.py
```

说明：
- `ros2 launch` 下交互式 stdin 不稳定
- 需要输入 `R/S` 的节点更推荐 `ros2 run`

## 终端交互

- 输入 `R` 开始录音
- 输入 `S` 停止录音

LLM 版本会打印：
- `ASR: ...`
- `LLM: ...`

## 依赖

- `pyaudio`
- `openai-whisper`
- 可选：`opencc-python-reimplemented`
- 如果使用大模型解析：对应 API Key 环境变量

如果工作区里存在 `.venv_whisper/bin/python3`，节点会自动切换到该 Python 解释器运行。
