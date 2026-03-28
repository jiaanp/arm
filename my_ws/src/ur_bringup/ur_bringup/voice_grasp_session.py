#!/usr/bin/env python3

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


class VoiceGraspSessionNode(Node):
    def __init__(self) -> None:
        super().__init__("voice_grasp_session")

        self.declare_parameter("request_topic", "/voice_grasp_request")
        self.declare_parameter("control_topic", "/grasp_session_control")
        self.declare_parameter("grasp_command_topic", "/grasp_command_text")
        self.declare_parameter("target_frame_topic", "/grasp_target_frame")
        self.declare_parameter("wrist_yaw_topic", "/wrist_target_yaw_delta")
        self.declare_parameter("wait_for_target_frame_sec", 600.0)
        self.declare_parameter("grasp_start_delay_sec", 1.0)
        self.declare_parameter("enable_wrist_yaw_refine", True)
        self.declare_parameter("grasp_close_position", 0.36)
        self.declare_parameter("grasp_settle_time_sec", 1.50)
        self.declare_parameter("grasp_x_offset", -0.012)
        self.declare_parameter("grasp_y_offset", 0.010)
        self.declare_parameter("grasp_z_offset", 0.140)
        self.declare_parameter("post_grasp_lift_height", 0.10)
        self.declare_parameter("pre_grasp_hover_distance", 0.08)
        self.declare_parameter("pre_grasp_pause_sec", 0.30)
        self.declare_parameter("wrist_yaw_is_delta", True)
        self.declare_parameter("wrist_yaw_max_age_sec", 0.60)
        self.declare_parameter("wrist_yaw_min_change_rad", 0.01)
        self.declare_parameter("wrist_yaw_settle_time_sec", 0.25)

        self.request_topic = str(self.get_parameter("request_topic").value)
        self.control_topic = str(self.get_parameter("control_topic").value)
        self.grasp_command_topic = str(self.get_parameter("grasp_command_topic").value)
        self.target_frame_topic = str(self.get_parameter("target_frame_topic").value)
        self.wrist_yaw_topic = str(self.get_parameter("wrist_yaw_topic").value)
        self.wait_for_target_frame_sec = float(self.get_parameter("wait_for_target_frame_sec").value)
        self.grasp_start_delay_sec = float(self.get_parameter("grasp_start_delay_sec").value)
        self.enable_wrist_yaw_refine = bool(self.get_parameter("enable_wrist_yaw_refine").value)
        self.grasp_close_position = float(self.get_parameter("grasp_close_position").value)
        self.grasp_settle_time_sec = float(self.get_parameter("grasp_settle_time_sec").value)
        self.grasp_x_offset = float(self.get_parameter("grasp_x_offset").value)
        self.grasp_y_offset = float(self.get_parameter("grasp_y_offset").value)
        self.grasp_z_offset = float(self.get_parameter("grasp_z_offset").value)
        self.post_grasp_lift_height = float(self.get_parameter("post_grasp_lift_height").value)
        self.pre_grasp_hover_distance = float(self.get_parameter("pre_grasp_hover_distance").value)
        self.pre_grasp_pause_sec = float(self.get_parameter("pre_grasp_pause_sec").value)
        self.wrist_yaw_is_delta = bool(self.get_parameter("wrist_yaw_is_delta").value)
        self.wrist_yaw_max_age_sec = float(self.get_parameter("wrist_yaw_max_age_sec").value)
        self.wrist_yaw_min_change_rad = float(self.get_parameter("wrist_yaw_min_change_rad").value)
        self.wrist_yaw_settle_time_sec = float(self.get_parameter("wrist_yaw_settle_time_sec").value)

        self.pending_commands: Deque[str] = deque()
        self.active_process: Optional[subprocess.Popen] = None
        self.active_command: Optional[str] = None
        self.lock = threading.Lock()

        self.create_subscription(String, self.request_topic, self.request_callback, 10)
        self.create_subscription(String, self.control_topic, self.control_callback, 10)
        self.create_timer(0.5, self.poll_active_process)
        threading.Thread(target=self.stdin_loop, daemon=True).start()

        self.get_logger().info(
            "Voice grasp session ready. "
            f"request_topic={self.request_topic}, control_topic={self.control_topic}"
        )
        self.get_logger().info("Type 'E' then Enter here to exit the grasp session.")

    def stdin_loop(self) -> None:
        while rclpy.ok():
            try:
                line = sys.stdin.readline()
            except Exception:
                return
            if not line:
                return
            if line.strip().upper() == 'E':
                self.get_logger().info("Exit requested from keyboard.")
                self.shutdown_session()
                return

    def request_callback(self, msg: String) -> None:
        command = msg.data.strip()
        if not command:
            self.get_logger().warn("Ignore empty grasp request.")
            return

        with self.lock:
            if self.active_process is None:
                self.start_grasp_process(command)
            else:
                self.pending_commands.append(command)
                self.get_logger().info(
                    f"Grasp busy. Queue command: {command} (pending={len(self.pending_commands)})"
                )

    def control_callback(self, msg: String) -> None:
        value = msg.data.strip().upper()
        if value in {'E', 'EXIT', 'QUIT'}:
            self.get_logger().info(f"Exit requested from control topic: {msg.data.strip()}")
            self.shutdown_session()

    def build_launch_command(self, command: str) -> list[str]:
        return [
            'ros2', 'launch', 'ur_bringup', 'start_grasp.launch.py',
            f'grasp_command_text:={command}',
            f'grasp_command_topic:={self.grasp_command_topic}',
            f'target_frame_topic:={self.target_frame_topic}',
            f'wrist_yaw_topic:={self.wrist_yaw_topic}',
            'grasp_all_if_no_target:=false',
            f'wait_for_target_frame_sec:={self.wait_for_target_frame_sec}',
            f'grasp_start_delay_sec:={self.grasp_start_delay_sec}',
            f'enable_wrist_yaw_refine:={str(self.enable_wrist_yaw_refine).lower()}',
            f'grasp_close_position:={self.grasp_close_position}',
            f'grasp_settle_time_sec:={self.grasp_settle_time_sec}',
            f'grasp_x_offset:={self.grasp_x_offset}',
            f'grasp_y_offset:={self.grasp_y_offset}',
            f'grasp_z_offset:={self.grasp_z_offset}',
            f'post_grasp_lift_height:={self.post_grasp_lift_height}',
            f'pre_grasp_hover_distance:={self.pre_grasp_hover_distance}',
            f'pre_grasp_pause_sec:={self.pre_grasp_pause_sec}',
            f'wrist_yaw_is_delta:={str(self.wrist_yaw_is_delta).lower()}',
            f'wrist_yaw_max_age_sec:={self.wrist_yaw_max_age_sec}',
            f'wrist_yaw_min_change_rad:={self.wrist_yaw_min_change_rad}',
            f'wrist_yaw_settle_time_sec:={self.wrist_yaw_settle_time_sec}',
        ]

    def start_grasp_process(self, command: str) -> None:
        launch_cmd = self.build_launch_command(command)
        self.get_logger().info(f"Start grasp command: {command}")
        self.active_command = command
        self.active_process = subprocess.Popen(launch_cmd, start_new_session=True)

    def poll_active_process(self) -> None:
        with self.lock:
            if self.active_process is None:
                return

            return_code = self.active_process.poll()
            if return_code is None:
                return

            finished_command = self.active_command or ''
            self.get_logger().info(
                f"Grasp process finished with code {return_code}: {finished_command}"
            )
            self.active_process = None
            self.active_command = None

            if self.pending_commands:
                next_command = self.pending_commands.popleft()
                self.get_logger().info(f"Start next queued command: {next_command}")
                self.start_grasp_process(next_command)
            else:
                self.get_logger().info("Waiting for next voice grasp command...")

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
            self.active_command = None

    def shutdown_session(self) -> None:
        with self.lock:
            self.pending_commands.clear()
            self.terminate_active_process()
        rclpy.shutdown()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VoiceGraspSessionNode()
    try:
        rclpy.spin(node)
    finally:
        node.shutdown_session()
        node.destroy_node()


if __name__ == '__main__':
    main()
