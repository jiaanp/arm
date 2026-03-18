#!/usr/bin/env python3
import os
import sys
from pathlib import Path

import rclpy
from rclpy.node import Node

try:
    from opencc import OpenCC
except ModuleNotFoundError:
    OpenCC = None


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

    if os.environ.get('_WHISPER_REEXEC_DONE') == '1':
        return

    os.environ['_WHISPER_REEXEC_DONE'] = '1'
    os.execv(str(target), [str(target), *sys.argv])


class WhisperAsrNode(Node):
    def __init__(self):
        super().__init__('whisper_asr')
        try:
            import whisper
        except ModuleNotFoundError:
            whisper = None

        if whisper is None:
            self.get_logger().error(
                'Missing dependency: whisper. Install with: pip install openai-whisper'
            )
            raise RuntimeError('whisper is not installed')

        default_audio = str(Path(__file__).resolve().parents[3] / 'output.wav')
        self.declare_parameter('audio_file', default_audio)
        self.declare_parameter('model', 'base')
        self.declare_parameter('language', 'zh')
        self.declare_parameter('force_simplified', True)
        default_download_root = str(Path.home() / '.cache' / 'whisper')
        self.declare_parameter('download_root', default_download_root)

        audio_path = Path(self.get_parameter('audio_file').value).expanduser().resolve()
        model_name = self.get_parameter('model').value
        language = self.get_parameter('language').value
        force_simplified = bool(self.get_parameter('force_simplified').value)
        download_root = Path(
            self.get_parameter('download_root').value
        ).expanduser().resolve()

        if not audio_path.exists():
            self.get_logger().error(f'Audio file not found: {audio_path}')
            raise FileNotFoundError(audio_path)

        download_root.mkdir(parents=True, exist_ok=True)
        self.get_logger().info(
            f'Start ASR with model={model_name}, file={audio_path}, download_root={download_root}'
        )

        asr_model = whisper.load_model(model_name, download_root=str(download_root))
        result = asr_model.transcribe(str(audio_path), language=language)

        text = ''
        if isinstance(result, dict):
            text = str(result.get('text', '')).strip()
        else:
            text = str(getattr(result, 'text', '')).strip()

        if text and force_simplified and language.startswith('zh'):
            if OpenCC is None:
                self.get_logger().error(
                    'Missing dependency: opencc. Install with: pip install opencc-python-reimplemented'
                )
                raise RuntimeError('opencc is not installed')
            text = OpenCC('t2s').convert(text)

        if text:
            self.get_logger().info(f'ASR text: {text}')
            print(text)
        else:
            self.get_logger().warn('ASR result is empty.')


def main(args=None):
    _maybe_reexec_to_venv_python()
    rclpy.init(args=args)
    node = WhisperAsrNode()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
