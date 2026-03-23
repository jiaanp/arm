#!/usr/bin/env python3

import json
import os
import re
import select
import sys
import wave
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

pyaudio = None
whisper = None
OpenCC = None

COLOR_ALIASES = {
    'red': '红色', '红': '红色', '红色': '红色',
    'blue': '蓝色', '蓝': '蓝色', '蓝色': '蓝色',
    'green': '绿色', '绿': '绿色', '绿色': '绿色',
    'yellow': '黄色', '黄': '黄色', '黄色': '黄色',
    'orange': '橙色', '橙': '橙色', '橙色': '橙色',
}

ZONE_ALIASES = {
    '左侧区域': 'left', '左边区域': 'left', '左边位置': 'left', '左侧位置': 'left', '左边': 'left', '左侧': 'left', '左': 'left',
    '中间区域': 'middle', '中央区域': 'middle', '中间位置': 'middle', '中央位置': 'middle', '中间': 'middle', '中央': 'middle',
    '右侧区域': 'right', '右边区域': 'right', '右边位置': 'right', '右侧位置': 'right', '右边': 'right', '右侧': 'right', '右': 'right',
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
    if os.environ.get('_VOICE_PICK_PLACE_REEXEC_DONE') == '1':
        return
    target = _resolve_venv_python()
    if target is None:
        return
    current = Path(sys.executable).absolute()
    if current == target:
        return
    os.environ['_VOICE_PICK_PLACE_REEXEC_DONE'] = '1'
    os.execv(str(target), [str(target), *sys.argv])


_maybe_reexec_to_venv_python()


class VoicePickPlaceCommandNode(Node):
    def __init__(self) -> None:
        super().__init__('voice_pick_place_command')
        default_audio = str(Path(__file__).resolve().parents[3] / 'output.wav')
        default_download_root = str(Path.home() / '.cache' / 'whisper')
        self.declare_parameter('request_topic', '/voice_pick_place_request')
        self.declare_parameter('audio_file', default_audio)
        self.declare_parameter('sample_rate', 16000)
        self.declare_parameter('channels', 1)
        self.declare_parameter('chunk', 1024)
        self.declare_parameter('asr_model', 'base')
        self.declare_parameter('asr_language', 'zh')
        self.declare_parameter('download_root', default_download_root)
        self.declare_parameter('force_simplified', True)
        self.request_topic = str(self.get_parameter('request_topic').value)
        self.audio_file = Path(str(self.get_parameter('audio_file').value)).expanduser().resolve()
        self.sample_rate = int(self.get_parameter('sample_rate').value)
        self.channels = int(self.get_parameter('channels').value)
        self.chunk = int(self.get_parameter('chunk').value)
        self.asr_model_name = str(self.get_parameter('asr_model').value)
        self.asr_language = str(self.get_parameter('asr_language').value)
        self.download_root = Path(str(self.get_parameter('download_root').value)).expanduser().resolve()
        self.force_simplified = bool(self.get_parameter('force_simplified').value)
        self.request_pub = self.create_publisher(String, self.request_topic, 10)

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

    def run_once(self) -> None:
        self._check_dependencies()
        audio_path = self._record_audio()
        raw_text = self._transcribe(audio_path)
        print(f'ASR: {raw_text}')
        if not raw_text:
            return
        request = self._normalize_request(raw_text)
        print(f'REQ: {request}')
        msg = String()
        msg.data = json.dumps(request, ensure_ascii=False)
        self.request_pub.publish(msg)

    def _record_audio(self) -> Path:
        self.audio_file.parent.mkdir(parents=True, exist_ok=True)
        print("Input 'R' then Enter to start recording.")
        while True:
            cmd = input().strip().upper()
            if cmd == 'R':
                break
        pa = pyaudio.PyAudio()
        stream = pa.open(format=pyaudio.paInt16, channels=self.channels, rate=self.sample_rate, input=True,
                         frames_per_buffer=self.chunk)
        frames = []
        print("Input 'S' then Enter to stop recording.")
        while True:
            frames.append(stream.read(self.chunk, exception_on_overflow=False))
            ready, _, _ = select.select([sys.stdin], [], [], 0)
            if ready and sys.stdin.readline().strip().upper() == 'S':
                break
        stream.stop_stream(); stream.close(); pa.terminate()
        with wave.open(str(self.audio_file), 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(b''.join(frames))
        return self.audio_file

    def _transcribe(self, audio_path: Path) -> str:
        self.download_root.mkdir(parents=True, exist_ok=True)
        model = whisper.load_model(self.asr_model_name, download_root=str(self.download_root))
        result = model.transcribe(str(audio_path), language=self.asr_language)
        text = str(result.get('text', '') if isinstance(result, dict) else getattr(result, 'text', '')).strip()
        if text and self.force_simplified and self.asr_language.startswith('zh') and OpenCC is not None:
            text = OpenCC('t2s').convert(text)
        return text

    def _extract_pick_command(self, text: str) -> str:
        pick_part = text.split('放到')[0].split('放在')[0].strip()
        if not pick_part.startswith('抓'):
            pick_part = '抓' + pick_part
        if '方块' not in pick_part:
            color = ''
            for key, value in COLOR_ALIASES.items():
                if key in text.lower() or key in text:
                    color = value
                    break
            if color:
                pick_part = f'抓{color}方块'
            else:
                pick_part = '抓方块'
        return pick_part

    def _extract_place_zone(self, text: str) -> str:
        place_part = text
        for marker in ('放到', '放在'):
            if marker in text:
                place_part = text.split(marker, 1)[1].strip()
                break
        place_part = place_part.replace('那里', '').replace('那边', '').replace('那儿', '').replace('去', '').strip()
        for key in sorted(ZONE_ALIASES.keys(), key=len, reverse=True):
            if key in place_part:
                return ZONE_ALIASES[key]
        return 'middle'

    def _normalize_request(self, raw_text: str) -> dict:
        return {
            'pick_command': self._extract_pick_command(raw_text),
            'place_zone': self._extract_place_zone(raw_text),
        }


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VoicePickPlaceCommandNode()
    try:
        node.run_once()
    finally:
        node.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()
