#!/usr/bin/env python3

import json
import os
import re
import select
import sys
import urllib.error
import urllib.request
import wave
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

pyaudio = None
whisper = None
OpenCC = None

COLOR_ALIASES = {
    'red': '红色',
    '红': '红色',
    '红色': '红色',
    'green': '绿色',
    '绿': '绿色',
    '绿色': '绿色',
    'blue': '蓝色',
    '蓝': '蓝色',
    '蓝色': '蓝色',
    'yellow': '黄色',
    '黄': '黄色',
    '黄色': '黄色',
    'orange': '橙色',
    '橙': '橙色',
    '橙色': '橙色',
}

POSITION_ALIASES = {
    'leftmost': '最左边',
    '最左': '最左边',
    '最左边': '最左边',
    'left': '最左边',
    'rightmost': '最右边',
    '最右': '最右边',
    '最右边': '最右边',
    'right': '最右边',
    'middle': '中间',
    '中间': '中间',
}

CHINESE_NUM_MAP = {
    '一': 1,
    '二': 2,
    '三': 3,
    '四': 4,
    '五': 5,
    '六': 6,
    '七': 7,
    '八': 8,
    '九': 9,
}


def _resolve_venv_python() -> Path | None:
    explicit = os.environ.get('WHISPER_VENV_PYTHON', '').strip()
    if explicit:
        path = Path(explicit).expanduser()
        if path.exists():
            return path.absolute()

    file_path = Path(__file__).resolve()
    search_roots = [Path.cwd().resolve(), file_path]
    search_roots.extend(file_path.parents)
    for root in search_roots:
        candidate = root / '.venv_whisper' / 'bin' / 'python3'
        if candidate.exists():
            return candidate.absolute()
    return None


def _maybe_reexec_to_venv_python() -> None:
    if os.environ.get('_VOICE_PICK_LLM_REEXEC_DONE') == '1':
        return

    target = _resolve_venv_python()
    if target is None:
        return

    current = Path(sys.executable).absolute()
    if current == target:
        return

    os.environ['_VOICE_PICK_LLM_REEXEC_DONE'] = '1'
    os.execv(str(target), [str(target), *sys.argv])


_maybe_reexec_to_venv_python()


class VoicePickLlmCommandNode(Node):
    def __init__(self) -> None:
        super().__init__('voice_pick_llm_command')

        default_audio = str(Path(__file__).resolve().parents[3] / 'output.wav')
        default_download_root = str(Path.home() / '.cache' / 'whisper')

        self.declare_parameter('command_topic', '/voice_grasp_request')
        self.declare_parameter('raw_text_topic', '/voice_pick_raw_text')
        self.declare_parameter('normalized_text_topic', '/voice_pick_llm_normalized_text')
        self.declare_parameter('audio_file', default_audio)
        self.declare_parameter('sample_rate', 16000)
        self.declare_parameter('channels', 1)
        self.declare_parameter('chunk', 1024)
        self.declare_parameter('asr_model', 'base')
        self.declare_parameter('asr_language', 'zh')
        self.declare_parameter('download_root', default_download_root)
        self.declare_parameter('force_simplified', True)
        self.declare_parameter('llm_api_key_env', 'DEEPSEEK_API_KEY')
        self.declare_parameter('llm_api_base', 'https://api.deepseek.com')
        self.declare_parameter('llm_model', 'deepseek-chat')
        self.declare_parameter('llm_timeout_sec', 15.0)
        self.declare_parameter('publish_rule_fallback', True)

        self.command_topic = str(self.get_parameter('command_topic').value)
        self.raw_text_topic = str(self.get_parameter('raw_text_topic').value)
        self.normalized_text_topic = str(self.get_parameter('normalized_text_topic').value)
        audio_file_value = str(self.get_parameter('audio_file').value).strip() or default_audio
        self.audio_file = Path(audio_file_value).expanduser().resolve()
        self.sample_rate = int(self.get_parameter('sample_rate').value)
        self.channels = int(self.get_parameter('channels').value)
        self.chunk = int(self.get_parameter('chunk').value)
        self.asr_model_name = str(self.get_parameter('asr_model').value)
        self.asr_language = str(self.get_parameter('asr_language').value)
        self.download_root = Path(str(self.get_parameter('download_root').value)).expanduser().resolve()
        self.force_simplified = bool(self.get_parameter('force_simplified').value)
        self.llm_api_key_env = str(self.get_parameter('llm_api_key_env').value)
        self.llm_api_base = str(self.get_parameter('llm_api_base').value).rstrip('/')
        self.llm_model = str(self.get_parameter('llm_model').value)
        self.llm_timeout_sec = float(self.get_parameter('llm_timeout_sec').value)
        self.publish_rule_fallback = bool(self.get_parameter('publish_rule_fallback').value)

        self.command_pub = self.create_publisher(String, self.command_topic, 10)
        self.raw_text_pub = self.create_publisher(String, self.raw_text_topic, 10)
        self.normalized_text_pub = self.create_publisher(String, self.normalized_text_topic, 10)

        self.get_logger().info(
            'Voice pick LLM command ready. '
            f'python={sys.executable}, command_topic={self.command_topic}, llm_model={self.llm_model}'
        )

    def _load_optional_dependencies(self) -> None:
        global pyaudio, whisper, OpenCC

        if pyaudio is None:
            try:
                import pyaudio as _pyaudio
                pyaudio = _pyaudio
            except ModuleNotFoundError:
                pass

        if whisper is None:
            try:
                import whisper as _whisper
                whisper = _whisper
            except ModuleNotFoundError:
                pass

        if OpenCC is None:
            try:
                from opencc import OpenCC as _OpenCC
                OpenCC = _OpenCC
            except ModuleNotFoundError:
                pass

    def _check_dependencies(self) -> None:
        self._load_optional_dependencies()
        missing = []
        if pyaudio is None:
            missing.append('pyaudio')
        if whisper is None:
            missing.append('openai-whisper')
        if missing:
            raise RuntimeError('Missing dependencies: ' + ', '.join(missing))

    def _publish_text(self, publisher, text: str) -> None:
        msg = String()
        msg.data = text
        publisher.publish(msg)

    def run_once(self) -> None:
        self._check_dependencies()
        audio_path = self._record_audio()
        raw_text = self._transcribe(audio_path)
        self._publish_text(self.raw_text_pub, raw_text)
        print(f'ASR: {raw_text}')
        if not raw_text:
            self.get_logger().warn('ASR text is empty, skip publish.')
            return

        normalized = self._normalize_with_llm(raw_text)
        self._publish_text(self.normalized_text_pub, normalized)
        print(f'CMD: {normalized}')
        self._publish_text(self.command_pub, normalized)
        self.get_logger().info(f'Published pick command: {normalized}')

    def _record_audio(self) -> Path:
        self.audio_file.parent.mkdir(parents=True, exist_ok=True)
        print("Input 'R' then Enter to start recording.")
        while True:
            cmd = input().strip().upper()
            if cmd == 'R':
                break
            self.get_logger().info("Invalid input. Please input 'R' then Enter.")

        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk,
        )

        self.get_logger().info(
            f"Recording at {self.sample_rate}Hz. Input 'S' then Enter to stop and save -> {self.audio_file}"
        )

        frames = []
        while True:
            frames.append(stream.read(self.chunk, exception_on_overflow=False))
            ready, _, _ = select.select([sys.stdin], [], [], 0)
            if ready:
                cmd = sys.stdin.readline().strip().upper()
                if cmd == 'S':
                    break

        stream.stop_stream()
        stream.close()
        pa.terminate()

        with wave.open(str(self.audio_file), 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(b''.join(frames))

        self.get_logger().info(f'Record done, saved to: {self.audio_file}')
        return self.audio_file

    def _transcribe(self, audio_path: Path) -> str:
        self.download_root.mkdir(parents=True, exist_ok=True)
        self.get_logger().info(
            f'Start ASR with model={self.asr_model_name}, file={audio_path}, download_root={self.download_root}'
        )
        asr_model = whisper.load_model(self.asr_model_name, download_root=str(self.download_root))
        result = asr_model.transcribe(str(audio_path), language=self.asr_language)

        if isinstance(result, dict):
            text = str(result.get('text', '')).strip()
        else:
            text = str(getattr(result, 'text', '')).strip()

        if text and self.force_simplified and self.asr_language.startswith('zh') and OpenCC is not None:
            text = OpenCC('t2s').convert(text)

        self.get_logger().info(f'ASR text: {text}')
        return text

    def _rule_extract_color(self, text: str) -> str:
        lowered = text.lower()
        for key, value in COLOR_ALIASES.items():
            if key in lowered or key in text:
                return value
        return ''

    def _rule_extract_position(self, text: str) -> str:
        lowered = text.lower()
        for key, value in POSITION_ALIASES.items():
            if key in lowered or key in text:
                return value
        return ''

    def _rule_extract_index(self, text: str) -> int:
        match = re.search(r'第\s*([1-9][0-9]*)\s*个', text)
        if match:
            return int(match.group(1))
        zh_match = re.search(r'第\s*([一二三四五六七八九])\s*个', text)
        if zh_match:
            return CHINESE_NUM_MAP.get(zh_match.group(1), 0)
        alt_match = re.search(r'([1-9][0-9]*)\s*个', text)
        if alt_match:
            return int(alt_match.group(1))
        return 0

    def _rule_normalize(self, raw_text: str) -> str:
        text = raw_text.strip()
        color = self._rule_extract_color(text)
        position = self._rule_extract_position(text)
        index = self._rule_extract_index(text)

        if index > 0 and color:
            return f'抓第{index}个{color}方块'
        if index > 0:
            return f'抓第{index}个方块'
        if position and color:
            return f'抓{position}的{color}方块'
        if position:
            return f'抓{position}的方块'
        if color:
            return f'抓{color}方块'
        return '抓方块'

    def _normalize_color(self, value: str) -> str:
        if not value:
            return ''
        lowered = value.strip().lower()
        for key, normalized in COLOR_ALIASES.items():
            if lowered == key.lower() or value.strip() == key:
                return normalized
        return ''

    def _normalize_position(self, value: str) -> str:
        if not value:
            return ''
        lowered = value.strip().lower()
        for key, normalized in POSITION_ALIASES.items():
            if lowered == key.lower() or value.strip() == key:
                return normalized
        return ''

    def _intent_to_command(self, intent: dict, raw_text: str) -> str:
        color = self._normalize_color(str(intent.get('color') or ''))
        position = self._normalize_position(str(intent.get('position') or ''))
        index = intent.get('index')
        try:
            index = int(index) if index is not None else 0
        except Exception:
            index = 0

        if index > 0 and color:
            return f'抓第{index}个{color}方块'
        if index > 0:
            return f'抓第{index}个方块'
        if position and color:
            return f'抓{position}的{color}方块'
        if position:
            return f'抓{position}的方块'
        if color:
            return f'抓{color}方块'
        return self._rule_normalize(raw_text)

    def _normalize_with_llm(self, raw_text: str) -> str:
        api_key = os.environ.get(self.llm_api_key_env, '').strip()
        if not api_key:
            if self.publish_rule_fallback:
                self.get_logger().warn(
                    f'Environment variable {self.llm_api_key_env} is empty, fallback to rule parser.'
                )
                return self._rule_normalize(raw_text)
            raise RuntimeError(f'Environment variable {self.llm_api_key_env} is empty.')

        system_prompt = (
            '你是机械臂抓取意图解析器。'
            '根据用户的一句中文口语命令，识别他想抓哪个方块。'
            '只输出严格 JSON，不要输出解释。'
            '字段固定为 action,color,position,index。'
            'action 只能是 pick。'
            'color 只能是 red,green,blue,yellow,orange,null。'
            'position 只能是 leftmost,rightmost,middle,null。'
            'index 只能是整数或 null。'
            '如果句子里同时出现位置和序号，优先保留更明确的那个。'
            '如果无法判断，就填 null。'
        )
        payload = {
            'model': self.llm_model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': raw_text},
            ],
            'temperature': 0.0,
            'response_format': {'type': 'json_object'},
            'stream': False,
        }
        request = urllib.request.Request(
            f'{self.llm_api_base}/chat/completions',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )

        try:
            with urllib.request.urlopen(request, timeout=self.llm_timeout_sec) as response:
                body = response.read().decode('utf-8')
            data = json.loads(body)
            content = data['choices'][0]['message']['content'].strip()
            intent = json.loads(content)
            self.get_logger().info(f'LLM intent: {intent}')
            return self._intent_to_command(intent, raw_text)
        except Exception as exc:
            if self.publish_rule_fallback:
                self.get_logger().warn(f'LLM parse failed, fallback to rule parser: {exc}')
                return self._rule_normalize(raw_text)
            raise


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VoicePickLlmCommandNode()
    try:
        node.run_once()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
