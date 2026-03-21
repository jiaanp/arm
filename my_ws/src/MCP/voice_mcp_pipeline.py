#!/usr/bin/env python3
import os
import json
import argparse
from pathlib import Path

import anyio
import sounddevice as sd
import soundfile as sf
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def record_audio_interactive(out_wav: str, sample_rate: int = 16000) -> str:
    print("\n输入 r 开始录音，输入 q 退出")
    while True:
        cmd = input("> ").strip().lower()
        if cmd == "q":
            raise SystemExit(0)
        if cmd == "r":
            break
        print("仅支持 r/q")

    frames = []

    def callback(indata, _frames, _time, _status):
        if _status:
            print(f"[audio status] {_status}")
        frames.append(indata.copy())

    print("录音中... 输入 r 停止录音")
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32", callback=callback):
        while True:
            cmd = input("> ").strip().lower()
            if cmd == "r":
                break
            if cmd == "q":
                raise SystemExit(0)
            print("录音中仅支持 r(停止)/q(退出)")

    if not frames:
        raise RuntimeError("没有录到音频，请重试。")

    audio = frames[0]
    for f in frames[1:]:
        audio = __import__("numpy").vstack((audio, f))

    sf.write(out_wav, audio, sample_rate)
    print(f"已保存音频: {out_wav}")
    return out_wav


def asr_with_whisper(audio_path: str, model_name: str = "base", language: str = "zh") -> str:
    import whisper
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path, language=language)
    return (result.get("text") or "").strip()


def build_openai_tools_from_mcp(mcp_tools):
    tools = []
    for t in mcp_tools:
        schema = getattr(t, "inputSchema", None) or {"type": "object", "properties": {}}
        tools.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": schema
            }
        })
    return tools


async def run_pipeline(server_path: str, user_text: str, api_key: str, model: str = "deepseek-chat"):
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    server = StdioServerParameters(command="python3", args=[server_path])

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            mcp_tools = tools_result.tools
            if not mcp_tools:
                raise RuntimeError("MCP server has no tools.")
            llm_tools = build_openai_tools_from_mcp(mcp_tools)

            messages = [
                {"role": "system", "content": "你是工具调度器，必须先调用工具，不要直接回答。"},
                {"role": "user", "content": user_text},
            ]

            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=llm_tools,
                tool_choice="required",
                temperature=0.1,
            )
            msg = resp.choices[0].message
            tool_calls = msg.tool_calls or []
            if not tool_calls:
                raise RuntimeError("DeepSeek did not call any tool.")

            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [tc.model_dump() for tc in tool_calls]
            })

            for tc in tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments or "{}")
                tool_ret = await session.call_tool(name, args)
                ret_text = ""
                if getattr(tool_ret, "content", None):
                    for c in tool_ret.content:
                        ret_text += (getattr(c, "text", None) or str(c)) + "\n"
                else:
                    ret_text = str(tool_ret)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": name,
                    "content": ret_text.strip()
                })

            final_resp = client.chat.completions.create(model=model, messages=messages, temperature=0.1)
            print("\n模型最终输出：")
            print(final_resp.choices[0].message.content or "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-path", default="/home/hw/arm-1/my_ws/src/MCP/server.py")
    parser.add_argument("--wav", default="/tmp/voice_cmd.wav")
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--whisper-model", default="base")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--text", default="")
    parser.add_argument("--model", default="deepseek-chat")
    args = parser.parse_args()

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Please set DEEPSEEK_API_KEY first.")

    Path(args.wav).parent.mkdir(parents=True, exist_ok=True)

    if args.text.strip():
        text = args.text.strip()
        anyio.run(run_pipeline, args.server_path, text, api_key, args.model)
        return

    while True:
        try:
            record_audio_interactive(args.wav, args.sample_rate)
            text = asr_with_whisper(args.wav, args.whisper_model, args.language)
            print(f"识别文本: {text}")
            if text.strip():
                anyio.run(run_pipeline, args.server_path, text, api_key, args.model)
            else:
                print("识别为空，请重试。")
            print("\n一轮完成。输入 r 开始下一轮，q 退出。")
        except SystemExit:
            print("退出。")
            break


if __name__ == "__main__":
    main()
