#!/usr/bin/env python3

import json
import os
import signal
import subprocess
import sys
import threading
from collections import deque
from typing import Deque, Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class PickPlaceSessionNode(Node):
    def __init__(self) -> None:
        super().__init__('pick_place_session')
        self.declare_parameter('request_topic', '/voice_pick_place_request')
        self.declare_parameter('control_topic', '/pick_place_session_control')
        self.request_topic = str(self.get_parameter('request_topic').value)
        self.control_topic = str(self.get_parameter('control_topic').value)
        self.pending_requests: Deque[dict] = deque()
        self.active_process: Optional[subprocess.Popen] = None
        self.active_request: Optional[dict] = None
        self.lock = threading.Lock()
        self.create_subscription(String, self.request_topic, self.request_callback, 10)
        self.create_subscription(String, self.control_topic, self.control_callback, 10)
        self.create_timer(0.5, self.poll_active_process)
        threading.Thread(target=self.stdin_loop, daemon=True).start()
        self.get_logger().info(f'Pick-place session ready. request_topic={self.request_topic}')
        self.get_logger().info("Type 'E' then Enter here to exit the pick-place session.")

    def stdin_loop(self) -> None:
        while rclpy.ok():
          line = sys.stdin.readline()
          if not line:
              return
          if line.strip().upper() == 'E':
              self.shutdown_session(); return

    def request_callback(self, msg: String) -> None:
        try:
            request = json.loads(msg.data)
        except Exception:
            self.get_logger().warn(f'Invalid request payload: {msg.data}')
            return
        if 'pick_command' not in request:
            self.get_logger().warn('Request missing pick_command')
            return
        with self.lock:
            if self.active_process is None:
                self.start_request(request)
            else:
                self.pending_requests.append(request)
                self.get_logger().info(f'Queue request: {request}')

    def control_callback(self, msg: String) -> None:
        if msg.data.strip().upper() in {'E', 'EXIT', 'QUIT'}:
            self.shutdown_session()

    def build_launch_command(self, request: dict) -> list[str]:
        return [
            'ros2', 'launch', 'ur5e_pick_place_control', 'start_pick_place.launch.py',
            f"grasp_command_text:={request.get('pick_command', '抓方块')}",
            f"place_zone:={request.get('place_zone', 'middle')}",
        ]

    def start_request(self, request: dict) -> None:
        self.get_logger().info(f'Start pick-place request: {request}')
        self.active_request = request
        self.active_process = subprocess.Popen(self.build_launch_command(request), start_new_session=True)

    def poll_active_process(self) -> None:
        with self.lock:
            if self.active_process is None:
                return
            rc = self.active_process.poll()
            if rc is None:
                return
            self.get_logger().info(f'Pick-place process finished with code {rc}: {self.active_request}')
            self.active_process = None
            self.active_request = None
            if self.pending_requests:
                next_request = self.pending_requests.popleft()
                self.start_request(next_request)
            else:
                self.get_logger().info('Waiting for next pick-place command...')

    def terminate_active_process(self) -> None:
        if self.active_process is None:
            return
        try:
            os.killpg(self.active_process.pid, signal.SIGINT)
            self.active_process.wait(timeout=5.0)
        except Exception:
            try:
                os.killpg(self.active_process.pid, signal.SIGKILL)
            except Exception:
                pass
        finally:
            self.active_process = None
            self.active_request = None

    def shutdown_session(self) -> None:
        with self.lock:
            self.pending_requests.clear()
            self.terminate_active_process()
        rclpy.shutdown()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PickPlaceSessionNode()
    try:
        rclpy.spin(node)
    finally:
        node.shutdown_session(); node.destroy_node()

if __name__ == '__main__':
    main()
