#!/usr/bin/env python3
import asyncio
import os
import select
import subprocess
import sys
import wave
from pathlib import Path

import rclpy
from rclpy.node import Node

try:
    from opencc import OpenCC
except ModuleNotFoundError:
    OpenCC = None

try:
    from openai import OpenAI
except ModuleNotFoundError:
    OpenAI = None

try:
    import pyaudio
except ModuleNotFoundError:
    pyaudio = None


def _resolve_venv_python() -> Path | None:
    explicit = os.environ.get('WHISPER_VENV_PYTHON', '').strip()
    if explicit:
        p = Path(explicit).expanduser()
        if p.exists():
            return p

    file_path = Path(__file__).absolute()
    search_roots = [Path.cwd().absolute(), file_path]
    search_roots.extend(file_path.parents)
    for root in search_roots:
        candidate = root / '.venv_whisper' / 'bin' / 'python3'
        if candidate.exists():
            return candidate.absolute()

    return None


def _maybe_reexec_to_venv_python():
    target = _resolve_venv_python()
    if target is None:
        return

    try:
        current = Path(sys.executable).absolute()
    except Exception:
        current = Path(sys.executable)

    if current == target:
        return

    if os.environ.get('_VOICE_CHAT_REEXEC_DONE') == '1':
        return

    os.environ['_VOICE_CHAT_REEXEC_DONE'] = '1'
    os.execv(str(target), [str(target), *sys.argv])


class VoiceChatPipelineNode(Node):
    def __init__(self):
        super().__init__('voice_chat_pipeline')
        self._check_deps()
        self._declare_params()

        audio_file = self._record_audio()
        user_text = self._asr(audio_file)
        answer_text = self._ask_llm(user_text)
        self._tts(answer_text)

    def _check_deps(self):
        missing = []
        if pyaudio is None:
            missing.append('pyaudio')
        if OpenAI is None:
            missing.append('openai')
        try:
            import whisper  # noqa: F401
        except ModuleNotFoundError:
            missing.append('openai-whisper')
        try:
            import edge_tts  # noqa: F401
        except ModuleNotFoundError:
            missing.append('edge-tts')

        if missing:
            self.get_logger().error(f'Missing dependencies: {missing}')
            raise RuntimeError('Please install missing dependencies first.')

    def _declare_params(self):
        default_ws = Path(__file__).resolve().parents[3]
        self.declare_parameter('audio_file', str(default_ws / 'output.wav'))
        self.declare_parameter('sample_rate', 16000)
        self.declare_parameter('channels', 1)
        self.declare_parameter('chunk', 1024)

        self.declare_parameter('asr_model', 'base')
        self.declare_parameter('asr_language', 'zh')
        self.declare_parameter('asr_force_simplified', True)
        self.declare_parameter('asr_download_root', str(Path.home() / '.cache' / 'whisper'))

        self.declare_parameter('llm_api_key_env', 'DEEPSEEK_API_KEY')
        self.declare_parameter('llm_base_url', 'https://api.deepseek.com')
        self.declare_parameter('llm_model', 'deepseek-chat')
        self.declare_parameter('llm_system_prompt', 'You are a helpful assistant')

        self.declare_parameter('tts_voice', 'zh-CN-XiaoxiaoNeural')
        self.declare_parameter('tts_rate', '+0%')
        self.declare_parameter('tts_volume', '+0%')
        self.declare_parameter('tts_output_file', str(default_ws / 'assistant_reply.mp3'))
        self.declare_parameter('tts_auto_play', True)

    def _record_audio(self) -> Path:
        output_path = Path(str(self.get_parameter('audio_file').value)).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sample_rate = int(self.get_parameter('sample_rate').value)
        channels = int(self.get_parameter('channels').value)
        chunk = int(self.get_parameter('chunk').value)
        sample_width = 2

        self.get_logger().info("Input 'R' then Enter to start recording.")
        while True:
            cmd = input().strip().upper()
            if cmd == 'R':
                break
            self.get_logger().info("Invalid input. Please input 'R' then Enter.")

        self.get_logger().info(
            f"Recording... Input 'S' then Enter to stop and save -> {output_path}"
        )
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk,
        )

        frames = []
        while True:
            frames.append(stream.read(chunk, exception_on_overflow=False))
            ready, _, _ = select.select([sys.stdin], [], [], 0)
            if ready:
                cmd = sys.stdin.readline().strip().upper()
                if cmd == 'S':
                    break

        stream.stop_stream()
        stream.close()
        pa.terminate()

        with wave.open(str(output_path), 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(frames))

        self.get_logger().info(f'Record done: {output_path}')
        return output_path

    def _asr(self, audio_file: Path) -> str:
        import whisper

        model_name = str(self.get_parameter('asr_model').value)
        language = str(self.get_parameter('asr_language').value)
        force_simplified = bool(self.get_parameter('asr_force_simplified').value)
        download_root = Path(
            str(self.get_parameter('asr_download_root').value)
        ).expanduser().resolve()
        download_root.mkdir(parents=True, exist_ok=True)

        self.get_logger().info(f'ASR start: model={model_name}, file={audio_file}')
        asr_model = whisper.load_model(model_name, download_root=str(download_root))
        result = asr_model.transcribe(str(audio_file), language=language)
        text = str(result.get('text', '') if isinstance(result, dict) else '').strip()

        if text and force_simplified and language.startswith('zh'):
            if OpenCC is None:
                self.get_logger().warn('opencc missing, skip simplified conversion.')
            else:
                text = OpenCC('t2s').convert(text)

        if not text:
            raise RuntimeError('ASR result is empty.')

        self.get_logger().info(f'User text: {text}')
        print(f'USER: {text}')
        return text

    def _ask_llm(self, user_text: str) -> str:
        key_env = str(self.get_parameter('llm_api_key_env').value)
        api_key = os.environ.get(key_env, '').strip()
        if not api_key:
            raise RuntimeError(f'Environment variable {key_env} is empty.')

        base_url = str(self.get_parameter('llm_base_url').value).strip()
        model = str(self.get_parameter('llm_model').value).strip()
        system_prompt = str(self.get_parameter('llm_system_prompt').value)

        client = OpenAI(api_key=api_key, base_url=base_url)
        self.get_logger().info(f'LLM request: model={model}, base_url={base_url}')
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            stream=False,
        )
        answer = (response.choices[0].message.content or '').strip()
        if not answer:
            raise RuntimeError('LLM answer is empty.')
        self.get_logger().info(f'LLM answer: {answer}')
        print(f'ASSISTANT: {answer}')
        return answer

    def _tts(self, text: str):
        import edge_tts

        voice = str(self.get_parameter('tts_voice').value)
        rate = str(self.get_parameter('tts_rate').value)
        volume = str(self.get_parameter('tts_volume').value)
        output_file = Path(str(self.get_parameter('tts_output_file').value)).expanduser().resolve()
        auto_play = bool(self.get_parameter('tts_auto_play').value)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        self.get_logger().info(f'TTS start: voice={voice}, output={output_file}')

        async def _synthesize():
            communicate = edge_tts.Communicate(
                text=text, voice=voice, rate=rate, volume=volume
            )
            await communicate.save(str(output_file))

        asyncio.run(_synthesize())
        self.get_logger().info(f'TTS done: {output_file}')

        if auto_play:
            commands = [
                ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'error', str(output_file)],
                ['mpg123', '-q', str(output_file)],
            ]
            for cmd in commands:
                try:
                    subprocess.run(cmd, check=True)
                    return
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
            self.get_logger().warn(
                'auto_play=true but no supported player found (ffplay/mpg123).'
            )


def main(args=None):
    _maybe_reexec_to_venv_python()
    rclpy.init(args=args)
    node = VoiceChatPipelineNode()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
