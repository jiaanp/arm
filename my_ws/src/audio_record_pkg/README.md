# audio_record_pkg 使用教程

## 1. 功能简介
`audio_record_pkg` 是一个 ROS 2 Python 功能包，包含以下能力：

- 录音保存为 `wav`
- Whisper 语音识别（ASR）
- 文本转语音（`pyttsx3` 与 `edge-tts` 两种方式）
- 语音对话流水线：录音 -> 识别 -> 大模型问答 -> 语音播报

## 2. 环境准备

建议在工作区使用虚拟环境：

```bash
cd /home/hw/arm-1/my_ws
source .venv_whisper/bin/activate
```

安装常用依赖（按需）：

```bash
python -m pip install -U openai openai-whisper edge-tts opencc-python-reimplemented pyttsx3
```

如果需要自动播放 `mp3`，安装播放器：

```bash
sudo apt-get install -y ffmpeg
# 或
sudo apt-get install -y mpg123
```

## 3. 编译与环境加载

```bash
cd /home/hw/arm-1/my_ws
colcon build --packages-select audio_record_pkg
source install/setup.bash
export ROS_LOG_DIR=/home/hw/arm-1/my_ws/.ros_log
```

## 4. API Key 配置

### DeepSeek（默认用于语音对话流水线）
```bash
export DEEPSEEK_API_KEY="你的deepseek_key"
```

### OpenAI（可选）
```bash
export OPENAI_API_KEY="你的openai_key"
```

> 注意：不要把 key 写进代码，避免上传 GitHub 泄露。

## 5. 功能使用

### 5.1 录音节点
```bash
ros2 run audio_record_pkg audio_record
```
运行后：
- 输入 `R` 回车开始录音
- 输入 `S` 回车停止录音并保存

### 5.2 Whisper 识别节点
```bash
ros2 run audio_record_pkg whisper_asr --ros-args \
  -p audio_file:=/home/hw/arm-1/my_ws/output.wav \
  -p model:=base \
  -p language:=zh \
  -p force_simplified:=true \
  -p download_root:=/home/hw/arm-1/my_ws/.whisper_cache
```

### 5.3 本地 TTS（pyttsx3）
```bash
ros2 run audio_record_pkg pyttx3_demo --ros-args \
  -p language:=zh \
  -p text:="你好，这是测试语音"
```

### 5.4 神经 TTS（edge-tts，音质更自然）
```bash
ros2 run audio_record_pkg edge_tts_demo --ros-args \
  -p text:="你好，这是更自然的语音演示" \
  -p voice:="zh-CN-XiaoxiaoNeural" \
  -p output_file:=/home/hw/arm-1/my_ws/edge_tts_output.mp3 \
  -p auto_play:=true
```

### 5.5 语音对话流水线（推荐）
```bash
ros2 run audio_record_pkg voice_chat_pipeline
```
流程：
1. 输入 `R` 开始录音  
2. 输入 `S` 停止录音  
3. Whisper 转文字  
4. 文本发送到大模型  
5. 大模型回复通过 edge-tts 播报

如需改为 OpenAI：
```bash
ros2 run audio_record_pkg voice_chat_pipeline --ros-args \
  -p llm_api_key_env:=OPENAI_API_KEY \
  -p llm_base_url:=https://api.openai.com/v1 \
  -p llm_model:=gpt-4o-mini
```

## 6. 脚本调用示例（非 ros2 run）

```bash
python3 /home/hw/arm-1/my_ws/src/audio_record_pkg/audio_record_pkg/deepseek_api.py
python3 /home/hw/arm-1/my_ws/src/audio_record_pkg/audio_record_pkg/math_ask_api.py
```

## 7. 常见问题

- 报 `Environment variable ... is empty`  
  原因：未设置 API Key 环境变量。

- 报 `insufficient_quota`  
  原因：API 账户额度不足或预算触顶。

- ALSA/JACK 大量日志  
  常见于音频设备探测，不一定是致命错误；重点看最终是否录音/播报成功。
