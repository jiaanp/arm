#!/usr/bin/env python3
import asyncio
import os
import subprocess
import sys
from pathlib import Path

import rclpy
from rclpy.node import Node


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

    if os.environ.get('_EDGE_TTS_REEXEC_DONE') == '1':
        return

    os.environ['_EDGE_TTS_REEXEC_DONE'] = '1'
    os.execv(str(target), [str(target), *sys.argv])


class EdgeTtsDemoNode(Node):
    def __init__(self):
        super().__init__('edge_tts_demo')
        try:
            import edge_tts
        except ModuleNotFoundError:
            edge_tts = None

        if edge_tts is None:
            self.get_logger().error(
                'Missing dependency: edge-tts. Install with: pip install edge-tts'
            )
            raise RuntimeError('edge-tts is not installed')

        default_output = str(Path(__file__).resolve().parents[3] / 'edge_tts_output.mp3')
        self.declare_parameter('text', '你好，这是更自然的语音合成演示。')
        self.declare_parameter('voice', 'zh-CN-XiaoxiaoNeural')
        self.declare_parameter('rate', '+0%')
        self.declare_parameter('volume', '+0%')
        self.declare_parameter('output_file', default_output)
        self.declare_parameter('auto_play', False)

        text = str(self.get_parameter('text').value)
        voice = str(self.get_parameter('voice').value)
        rate = str(self.get_parameter('rate').value)
        volume = str(self.get_parameter('volume').value)
        output_file = Path(str(self.get_parameter('output_file').value)).expanduser().resolve()
        auto_play = bool(self.get_parameter('auto_play').value)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        self.get_logger().info(
            f'Start edge-tts with voice={voice}, output={output_file}'
        )
        asyncio.run(self._synthesize(text, voice, rate, volume, output_file))
        self.get_logger().info(f'TTS finished: {output_file}')

        if auto_play:
            self._play_audio(output_file)

    async def _synthesize(self, text, voice, rate, volume, output_file):
        import edge_tts
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume)
        await communicate.save(str(output_file))

    def _play_audio(self, output_file: Path):
        # Prefer ffplay; if unavailable, fallback to mpg123.
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
    node = EdgeTtsDemoNode()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
