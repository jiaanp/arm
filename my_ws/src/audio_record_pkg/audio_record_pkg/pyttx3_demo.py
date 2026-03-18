#!/usr/bin/env python3
import re

import rclpy
from rclpy.node import Node

try:
    import pyttsx3
except ModuleNotFoundError:
    pyttsx3 = None


class Pyttx3DemoNode(Node):
    @staticmethod
    def _select_voice(engine, language: str):
        voices = engine.getProperty('voices') or []
        lang_key = language.lower()
        for v in voices:
            blob = f"{getattr(v, 'id', '')} {getattr(v, 'name', '')}".lower()
            if lang_key in blob:
                return v
            if lang_key.startswith('zh') and re.search(r'zh|chinese|mandarin', blob):
                return v
            if lang_key.startswith('en') and re.search(r'en|english', blob):
                return v
        return None

    def __init__(self):
        super().__init__('pyttx3_demo')
        if pyttsx3 is None:
            self.get_logger().error(
                'Missing dependency: pyttsx3. Install with: pip install pyttsx3'
            )
            raise RuntimeError('pyttsx3 is not installed')

        self.declare_parameter('text', '你好，这是 pyttx3 文本转语音演示。')
        self.declare_parameter('language', 'zh')
        self.declare_parameter('rate', 170)
        self.declare_parameter('volume', 1.0)

        text = str(self.get_parameter('text').value)
        language = str(self.get_parameter('language').value)
        rate = int(self.get_parameter('rate').value)
        volume = float(self.get_parameter('volume').value)

        self.get_logger().info(f'Start TTS text: {text}')
        engine = pyttsx3.init()
        selected = self._select_voice(engine, language)
        if selected is None:
            ids = [f"{getattr(v, 'id', '')} ({getattr(v, 'name', '')})" for v in engine.getProperty('voices') or []]
            self.get_logger().error(
                f"No voice found for language='{language}'. Available voices: {ids}"
            )
            raise RuntimeError('No matching voice found')

        engine.setProperty('voice', selected.id)
        engine.setProperty('rate', rate)
        engine.setProperty('volume', max(0.0, min(1.0, volume)))
        engine.say(text)
        engine.runAndWait()
        self.get_logger().info('TTS finished.')


def main(args=None):
    rclpy.init(args=args)
    node = Pyttx3DemoNode()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
