# voice_pick_bridge

独立语音抓取桥接包，专门处理“抓哪个”的命令。

主要节点：
- `voice_pick_command`: 规则版解析
- `voice_pick_llm_command`: 大模型解析 + 规则兜底

默认输出到：
- `/voice_grasp_request`

## 支持的抓取语义

- 指定颜色
- 最左边 / 最右边
- 第几个
- 颜色与位置、序号组合

示例：
- `抓最左边的红色方块`
- `抓最右边的蓝色方块`
- `抓第2个黄色方块`
- `抓红色方块`

终端会打印：
- `ASR: ...`
- `CMD: ...`

## 构建

```bash
cd /home/hw/arm-1/my_ws
colcon build --packages-select voice_pick_bridge
source install/setup.bash
```

## 运行

规则版：

```bash
ros2 run voice_pick_bridge voice_pick_command
```

LLM 版：

```bash
ros2 run voice_pick_bridge voice_pick_llm_command
```

也提供 launch：

```bash
ros2 launch voice_pick_bridge voice_pick_command.launch.py
ros2 launch voice_pick_bridge voice_pick_llm_command.launch.py
```

说明：
- 交互式录音更推荐 `ros2 run`
- LLM 版默认读取 `DEEPSEEK_API_KEY`

## 与抓取会话配合

推荐和下面这个会话启动一起用：

```bash
ros2 launch ur_bringup voice_triggered_grasp.launch.py
```

完整三终端流程见工作区总 README。
