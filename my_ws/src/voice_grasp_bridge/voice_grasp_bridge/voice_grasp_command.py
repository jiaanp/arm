#!/usr/bin/env python3

import os
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


def _resolve_venv_python() -> Path | None:
    explicit = os.environ.get("WHISPER_VENV_PYTHON", "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        if path.exists():
            return path.absolute()

    file_path = Path(__file__).resolve()
    search_roots = [Path.cwd().resolve(), file_path]
    search_roots.extend(file_path.parents)
    for root in search_roots:
        candidate = root / ".venv_whisper" / "bin" / "python3"
        if candidate.exists():
            return candidate.absolute()
    return None


def _maybe_reexec_to_venv_python() -> None:
    if os.environ.get("_VOICE_GRASP_REEXEC_DONE") == "1":
        return

    target = _resolve_venv_python()
    if target is None:
        return

    current = Path(sys.executable).absolute()
    if current == target:
        return

    os.environ["_VOICE_GRASP_REEXEC_DONE"] = "1"
    os.execv(str(target), [str(target), *sys.argv])


_maybe_reexec_to_venv_python()


class VoiceGraspCommandNode(Node):
    def __init__(self) -> None:
        super().__init__("voice_grasp_command")

        default_audio = str(Path(__file__).resolve().parents[3] / "output.wav")
        default_download_root = str(Path.home() / ".cache" / "whisper")

        self.declare_parameter("command_topic", "/grasp_command_text")
        self.declare_parameter("audio_file", default_audio)
        self.declare_parameter("sample_rate", 16000)
        self.declare_parameter("channels", 1)
        self.declare_parameter("chunk", 1024)
        self.declare_parameter("asr_model", "base")
        self.declare_parameter("asr_language", "zh")
        self.declare_parameter("download_root", default_download_root)
        self.declare_parameter("force_simplified", True)
        self.declare_parameter("publish_empty", False)

        self.command_topic = str(self.get_parameter("command_topic").value)
        audio_file_value = str(self.get_parameter("audio_file").value).strip()
        if not audio_file_value:
            audio_file_value = default_audio
        self.audio_file = Path(audio_file_value).expanduser().resolve()
        self.sample_rate = int(self.get_parameter("sample_rate").value)
        self.channels = int(self.get_parameter("channels").value)
        self.chunk = int(self.get_parameter("chunk").value)
        self.asr_model_name = str(self.get_parameter("asr_model").value)
        self.asr_language = str(self.get_parameter("asr_language").value)
        self.download_root = Path(str(self.get_parameter("download_root").value)).expanduser().resolve()
        self.force_simplified = bool(self.get_parameter("force_simplified").value)
        self.publish_empty = bool(self.get_parameter("publish_empty").value)

        self.publisher = self.create_publisher(String, self.command_topic, 10)

        self.get_logger().info(
            "Voice grasp bridge ready. "
            f"python={sys.executable}, command_topic={self.command_topic}, asr_model={self.asr_model_name}"
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

    def run_once(self) -> None:
        self._check_dependencies()
        audio_path = self._record_audio()
        text = self._transcribe(audio_path)
        if not text and not self.publish_empty:
            self.get_logger().warn("ASR text is empty, skip publish.")
            return

        msg = String()
        msg.data = text
        self.publisher.publish(msg)
        self.get_logger().info(f"Published grasp command: {text}")

    def _check_dependencies(self) -> None:
        self._load_optional_dependencies()
        missing = []
        if pyaudio is None:
            missing.append("pyaudio")
        if whisper is None:
            missing.append("openai-whisper")
        if missing:
            raise RuntimeError("Missing dependencies: " + ", ".join(missing))

    def _record_audio(self) -> Path:
        self.audio_file.parent.mkdir(parents=True, exist_ok=True)

        print("Input 'R' then Enter to start recording.")
        while True:
            cmd = input().strip().upper()
            if cmd == "R":
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
            f"Recording at {self.sample_rate}Hz. "
            f"Input 'S' then Enter to stop and save -> {self.audio_file}"
        )

        frames = []
        while True:
            frames.append(stream.read(self.chunk, exception_on_overflow=False))
            ready, _, _ = select.select([sys.stdin], [], [], 0)
            if ready:
                cmd = sys.stdin.readline().strip().upper()
                if cmd == "S":
                    break

        stream.stop_stream()
        stream.close()
        pa.terminate()

        with wave.open(str(self.audio_file), "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(b"".join(frames))

        self.get_logger().info(f"Record done, saved to: {self.audio_file}")
        return self.audio_file

    def _transcribe(self, audio_path: Path) -> str:
        self.download_root.mkdir(parents=True, exist_ok=True)
        self.get_logger().info(
            f"Start ASR with model={self.asr_model_name}, file={audio_path}, "
            f"download_root={self.download_root}"
        )

        asr_model = whisper.load_model(self.asr_model_name, download_root=str(self.download_root))
        result = asr_model.transcribe(str(audio_path), language=self.asr_language)

        text = ""
        if isinstance(result, dict):
            text = str(result.get("text", "")).strip()
        else:
            text = str(getattr(result, "text", "")).strip()

        if text and self.force_simplified and self.asr_language.startswith("zh") and OpenCC is not None:
            text = OpenCC("t2s").convert(text)

        self.get_logger().info(f"ASR text: {text}")
        return text


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VoiceGraspCommandNode()
    try:
        node.run_once()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
