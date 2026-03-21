# MCP（Model Context Protocol）工具集

这个文件夹包含了 Model Context Protocol (MCP) 的实现和相关工具，用于集成各种 AI 服务和工具的功能。

## 📁 文件说明

### 1. **server.py** - MCP 服务器
一个基于 FastMCP 框架的最小化 MCP 服务器实现。

**功能：**
- 基于 FastMCP 框架构建
- 提供 ADD 工具（两个数字相加）

**使用方法：**
```bash
python server.py
```

**示例工具：**
- `ADD(a: float, b: float) -> float` - 返回两个数字的和

### 2. **mcp_client.py** - MCP 客户端
一个 MCP 客户端示例，展示如何连接到 MCP 服务器并调用工具。

**功能：**
- 通过 stdio 连接到服务器
- 调用服务器提供的工具
- 接收和处理结果

**使用方法：**
```bash
python mcp_client.py
```

**工作流程：**
1. 启动 `server.py` 作为子进程
2. 建立 MCP 连接
3. 调用 ADD 工具并获取结果

### 3. **voice_mcp_pipeline.py** - 语音处理管道
一个完整的语音识别和 AI 工具调用管道，集成了音频处理、语音识别和 LLM 功能。

**主要功能：**
- 🎤 **音频录制** - 交互式音频录制（使用 sounddevice）
- 🗣️ **语音识别** - 基于 Whisper 的语音转文字
- 🤖 **LLM 集成** - 使用 DeepSeek 大模型进行推理
- 🛠️ **工具调用** - 通过 MCP 调用外部工具

## 🚀 快速开始

### 环境要求
```bash
pip install anyio sounddevice soundfile openai mcp fastmcp whisper
```

### 环境变量配置
```bash
export DEEPSEEK_API_KEY="your-api-key-here"
```

### 基本使用

#### 方式一：语音输入（交互式录音）
```bash
python voice_mcp_pipeline.py
```

按照提示：
- 输入 `r` 开始录音
- 输入 `r` 停止录音
- 输入 `q` 退出

#### 方式二：文本输入（跳过录音）
```bash
python voice_mcp_pipeline.py --text "你的文本命令"
```

## 📋 命令行参数

`voice_mcp_pipeline.py` 支持以下参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--server-path` | `/home/hw/arm-1/my_ws/src/MCP/server.py` | MCP 服务器路径 |
| `--wav` | `/tmp/voice_cmd.wav` | 音频文件保存路径 |
| `--sample-rate` | `16000` | 音频采样率 |
| `--whisper-model` | `base` | Whisper 模型大小 (tiny, base, small, medium, large) |
| `--language` | `zh` | 语言代码 (zh 中文, en 英文) |
| `--text` | 空 | 直接输入文本，跳过录音 |
| `--model` | `deepseek-chat` | 使用的 LLM 模型 |

## 💡 使用示例

### 示例 1：语音命令调用
```bash
# 简单的语音输入
python voice_mcp_pipeline.py

# 自定义保存路径
python voice_mcp_pipeline.py --wav /path/to/audio.wav

# 使用 large Whisper 模型提高准确率
python voice_mcp_pipeline.py --whisper-model large
```

### 示例 2：直接文本输入
```bash
python voice_mcp_pipeline.py --text "请帮我计算 3 加 5"
```

### 示例 3：自定义所有参数
```bash
python voice_mcp_pipeline.py \
  --text "执行加法操作" \
  --server-path "/path/to/server.py" \
  --model "your-model-name" \
  --language zh
```

## 🔄 工作流程

### voice_mcp_pipeline.py 完整流程图

```
┌─────────────────┐
│   输入音频/文本  │
└────────┬────────┘
         │
         ├─► 音频录制 (sounddevice)
         │     ↓
         ├─► Whisper 语音识别
         │     ↓
         ├─► 文本输入
         │
     ┌───┴─────────────────┐
     ▼                     ▼
  DeepSeek LLM 决策是否调用工具
     │
     ├─► 启动 MCP Server
     │     ↓
     ├─► 列出可用工具
     │     ↓
     ├─► 调用 Tool (e.g., ADD)
     │     ↓
     └─► 处理工具结果
           ↓
        返回最终输出
```

## 🛠️ 工作原理说明

### 1. 音频录制
- 使用 `sounddevice` 实时录制音频
- 采样率默认为 16kHz
- 支持交互式操作（r 开始/停止，q 退出）

### 2. 语音识别
- 使用 OpenAI 的 Whisper 模型
- 支持多种语言（默认中文）
- 模型大小从 tiny 到 large，越大越精准

### 3. LLM 推理
- 使用 DeepSeek API
- 系统提示强制模型先调用工具再回答
- 支持 function calling 机制

### 4. MCP 工具调用
- 通过 stdio 与 MCP 服务器通信
- 动态获取服务器提供的工具列表
- 将工具响应返还给 LLM 进行最终处理

## 🔐 安全性建议

- ⚠️ **API KEY 管理**：使用环境变量存储 `DEEPSEEK_API_KEY`，不要硬编码在代码中
- ⚠️ **音频文件**：录制的音频文件可能包含敏感信息，请定期清理
- ⚠️ **权限控制**：MCP 服务器的工具应仅允许安全操作

## 📦 依赖包

| 包名 | 用途 |
|-----|------|
| `anyio` | 异步 I/O 库 |
| `sounddevice` | 音频设备交互 |
| `soundfile` | 音频文件读写 |
| `openai` | OpenAI/DeepSeek API 客户端 |
| `mcp` | Model Context Protocol 库 |
| `fastmcp` | 简化 MCP 服务器开发 |
| `whisper` | OpenAI 语音识别模型 |

## 🐛 常见问题

### Q: 运行时出现 "DEEPSEEK_API_KEY not set" 错误
**A:** 需要设置环境变量：
```bash
export DEEPSEEK_API_KEY="你的API密钥"
```

### Q: Whisper 模型加载很慢
**A:** 首次加载会下载模型文件（较大）。可以使用更小的模型：
```bash
python voice_mcp_pipeline.py --whisper-model tiny
```

### Q: 找不到音频输入设备
**A:** 检查系统音频设备：
```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```

### Q: MCP 服务器连接失败
**A:** 确保 `server.py` 文件路径正确，且拥有执行权限

## 📝 扩展开发

### 添加自定义工具

在 `server.py` 中添加新工具：

```python
from fastmcp import FastMCP

mcp = FastMCP("custom-server")

@mcp.tool(name="MULTIPLY", description="Multiply two numbers")
def multiply(a: float, b: float) -> float:
    return a * b

if __name__ == "__main__":
    mcp.run()
```

### 修改系统提示

编辑 `voice_mcp_pipeline.py` 中的系统提示（约 85 行）来改变 LLM 的行为。

## 🔗 相关资源

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP 文档](https://github.com/jlowin/fastmcp)
- [DeepSeek API](https://platform.deepseek.com/)
- [OpenAI Whisper](https://github.com/openai/whisper)

---

**最后更新：** 2026年3月21日
