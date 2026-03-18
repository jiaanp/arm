#!/usr/bin/env python3
import select
import sys
import wave
from pathlib import Path

import rclpy
from rclpy.node import Node

try:
    import pyaudio
except ModuleNotFoundError:
    pyaudio = None


class AudioRecordNode(Node):
    def __init__(self):
        super().__init__('audio_record')
        if pyaudio is None:
            self.get_logger().error(
                'Missing dependency: pyaudio. Please install python3-pyaudio first.'
            )
            raise RuntimeError('pyaudio is not installed')

        default_output = str(Path(__file__).resolve().parents[3] / 'output.wav')
        self.declare_parameter('output_file', default_output)
        output_path = Path(self.get_parameter('output_file').value).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        sample_rate = 16000
        channels = 1
        sample_width = 2
        chunk = 1024
        self.get_logger().info("Input 'R' then Enter to start recording.")
        while True:
            cmd = input().strip().upper()
            if cmd == 'R':
                break
            self.get_logger().info("Invalid input. Please input 'R' then Enter.")

        self.get_logger().info(
            f"Recording at {sample_rate}Hz. Input 'S' then Enter to stop and save -> {output_path}"
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

        self.get_logger().info(f'Record done, saved to: {output_path}')


def main(args=None):
    rclpy.init(args=args)
    node = AudioRecordNode()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
