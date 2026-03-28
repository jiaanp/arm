#!/usr/bin/env python3
import argparse
from pathlib import Path

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image


def image_msg_to_bgr(msg: Image) -> np.ndarray:
    encoding = msg.encoding.lower()
    channels_map = {
        'bgr8': 3,
        'rgb8': 3,
        'bgra8': 4,
        'rgba8': 4,
        'mono8': 1,
    }
    if encoding not in channels_map:
        raise ValueError(f'unsupported image encoding: {msg.encoding}')

    channels = channels_map[encoding]
    expected_bytes = msg.height * msg.step
    array = np.frombuffer(msg.data, dtype=np.uint8)
    if array.size < expected_bytes:
        raise ValueError(
            f'image buffer too small: got {array.size} bytes, expected at least {expected_bytes}'
        )

    array = array[:expected_bytes].reshape((msg.height, msg.step))
    row_width = msg.width * channels
    array = array[:, :row_width]

    if channels == 1:
        gray = array.reshape((msg.height, msg.width)).copy()
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    image = array.reshape((msg.height, msg.width, channels)).copy()
    if encoding == 'bgr8':
        return image
    if encoding == 'rgb8':
        return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    if encoding == 'bgra8':
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    if encoding == 'rgba8':
        return cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)

    raise ValueError(f'unhandled image encoding: {msg.encoding}')


class RecordRosImages(Node):
    def __init__(self, output_dir: Path, image_topic: str, interval_sec: float, init_index: int):
        super().__init__('my_yolov11_record_ros_images')
        self.output_dir = output_dir
        self.image_topic = image_topic
        self.interval_sec = interval_sec
        self.index = init_index
        self.latest_msg = None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.create_subscription(Image, self.image_topic, self.image_callback, 10)
        self.create_timer(self.interval_sec, self.timer_callback)

        self.get_logger().info(
            f'recording topic={self.image_topic} -> {self.output_dir}, interval={self.interval_sec}s, start_index={self.index}'
        )

    def image_callback(self, msg: Image):
        self.latest_msg = msg

    def timer_callback(self):
        if self.latest_msg is None:
            self.get_logger().warn('no image received yet')
            return

        try:
            image = image_msg_to_bgr(self.latest_msg)
        except Exception as exc:
            self.get_logger().error(f'failed to decode ROS image: {exc}')
            return

        save_path = self.output_dir / f'{self.index:06d}.jpg'
        ok = cv2.imwrite(str(save_path), image)
        if not ok:
            self.get_logger().error(f'failed to save image: {save_path}')
            return

        self.get_logger().info(f'saved {save_path.name}')
        self.index += 1


def parse_args():
    parser = argparse.ArgumentParser(description='Record ROS images into my_yolov11/raw/images.')
    parser.add_argument('--output-dir', default='/home/hw/arm-1/my_ws/src/my_yolov11/raw/images')
    parser.add_argument('--image-topic', default='/color/image_raw')
    parser.add_argument('--interval-sec', type=float, default=3.0)
    parser.add_argument('--init-index', type=int, default=0)
    return parser.parse_args()


def main():
    args = parse_args()
    rclpy.init()
    node = RecordRosImages(
        output_dir=Path(args.output_dir).expanduser().resolve(),
        image_topic=args.image_topic,
        interval_sec=args.interval_sec,
        init_index=args.init_index,
    )
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
