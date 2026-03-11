import json
import os
import re
import threading
import urllib.error
import urllib.request
from typing import Dict, List, Optional

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from vision_msgs.msg import Detection2DArray


def normalize_color_name(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    text = raw.strip().lower()
    mapping = {
        "red": "red",
        "r": "red",
        "红": "red",
        "红色": "red",
        "green": "green",
        "g": "green",
        "绿": "green",
        "绿色": "green",
        "blue": "blue",
        "b": "blue",
        "蓝": "blue",
        "蓝色": "blue",
        "yellow": "yellow",
        "y": "yellow",
        "黄": "yellow",
        "黄色": "yellow",
        "orange": "orange",
        "橙": "orange",
        "橙色": "orange",
        "all": "all",
        "any": "all",
        "任意": "all",
        "全部": "all",
    }
    return mapping.get(text, text if text in {"red", "green", "blue", "yellow", "orange", "all"} else None)


def normalize_position_name(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    text = raw.strip().lower()
    mapping = {
        "left": "leftmost",
        "leftmost": "leftmost",
        "最左": "leftmost",
        "最左边": "leftmost",
        "left side": "leftmost",
        "right": "rightmost",
        "rightmost": "rightmost",
        "最右": "rightmost",
        "最右边": "rightmost",
        "right side": "rightmost",
        "middle": "middle",
        "center": "middle",
        "中间": "middle",
        "中间的": "middle",
        "any": "any",
        "任意": "any",
    }
    return mapping.get(text, text if text in {"leftmost", "rightmost", "middle", "any"} else None)


class OpenAISelector(Node):
    def __init__(self) -> None:
        super().__init__("openai_selector")

        self.declare_parameter("command_topic", "/grasp_command_text")
        self.declare_parameter("target_frame_topic", "/grasp_target_frame")
        self.declare_parameter("target_color_topic", "/wrist_target_color")
        self.declare_parameter("detection_topic", "/detection")
        self.declare_parameter("image_topic", "/color/image_raw")
        self.declare_parameter("model", "gpt-4.1-mini")
        self.declare_parameter("api_base", "https://api.openai.com/v1")
        self.declare_parameter("temperature", 0.0)
        self.declare_parameter("timeout_sec", 8.0)
        self.declare_parameter("use_llm", True)
        self.declare_parameter("fallback_only", False)
        self.declare_parameter("min_color_ratio", 0.015)
        self.declare_parameter("default_color_if_unknown", "all")

        self.command_topic = str(self.get_parameter("command_topic").value)
        self.target_frame_topic = str(self.get_parameter("target_frame_topic").value)
        self.target_color_topic = str(self.get_parameter("target_color_topic").value)
        self.detection_topic = str(self.get_parameter("detection_topic").value)
        self.image_topic = str(self.get_parameter("image_topic").value)
        self.model = str(self.get_parameter("model").value)
        self.api_base = str(self.get_parameter("api_base").value).rstrip("/")
        self.temperature = float(self.get_parameter("temperature").value)
        self.timeout_sec = float(self.get_parameter("timeout_sec").value)
        self.use_llm = bool(self.get_parameter("use_llm").value)
        self.fallback_only = bool(self.get_parameter("fallback_only").value)
        self.min_color_ratio = float(self.get_parameter("min_color_ratio").value)
        self.default_color_if_unknown = str(self.get_parameter("default_color_if_unknown").value)

        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if self.use_llm and not self.api_key:
            self.get_logger().warn(
                "OpenAI API key not found. Set env 'OPENAI_API_KEY' to enable LLM parsing."
            )

        self.bridge = CvBridge()
        self.lock = threading.Lock()
        self.latest_image: Optional[np.ndarray] = None
        self.latest_detections: List[Dict] = []

        self.frame_pub = self.create_publisher(String, self.target_frame_topic, 10)
        self.color_pub = self.create_publisher(String, self.target_color_topic, 10)
        self.create_subscription(String, self.command_topic, self.command_callback, 10)
        self.create_subscription(Detection2DArray, self.detection_topic, self.detection_callback, 10)
        self.create_subscription(Image, self.image_topic, self.image_callback, 10)

        self.color_hsv_ranges = {
            "red": [((0, 80, 50), (10, 255, 255)), ((170, 80, 50), (180, 255, 255))],
            "green": [((35, 60, 40), (90, 255, 255))],
            "blue": [((95, 80, 40), (135, 255, 255))],
            "yellow": [((18, 80, 80), (35, 255, 255))],
            "orange": [((8, 80, 80), (20, 255, 255))],
        }

        self.get_logger().info(
            "OpenAI selector started. "
            f"command_topic={self.command_topic}, detection_topic={self.detection_topic}, "
            f"target_frame_topic={self.target_frame_topic}"
        )

    def image_callback(self, msg: Image) -> None:
        try:
            img = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().warn(f"Failed to decode image: {exc}")
            return
        with self.lock:
            self.latest_image = img

    def detection_callback(self, msg: Detection2DArray) -> None:
        dets = []
        for det in msg.detections:
            cx = float(det.bbox.center.position.x)
            cy = float(det.bbox.center.position.y)
            sx = float(det.bbox.size_x)
            sy = float(det.bbox.size_y)
            dets.append({"cx": cx, "cy": cy, "sx": sx, "sy": sy})
        dets.sort(key=lambda d: d["cx"])
        for i, det in enumerate(dets, start=1):
            det["rank"] = i
            det["frame_id"] = f"cube{i}"
        with self.lock:
            self.latest_detections = dets

    def command_callback(self, msg: String) -> None:
        command = msg.data.strip()
        if not command:
            return

        scene = self.build_scene_snapshot()
        if not scene:
            self.get_logger().warn("No scene candidates available when command received.")
            return

        parsed = None
        if self.use_llm and not self.fallback_only and self.api_key:
            parsed = self.parse_with_llm(command, scene)
        if parsed is None:
            parsed = self.parse_with_fallback(command)

        selected = self.resolve_target(parsed, scene)
        if selected is None:
            self.get_logger().warn(f"Failed to resolve target for command: {command}")
            return

        frame_msg = String()
        frame_msg.data = selected["frame_id"]
        self.frame_pub.publish(frame_msg)

        color_msg = String()
        color = parsed.get("color")
        norm_color = normalize_color_name(color)
        if norm_color is None or norm_color == "all":
            norm_color = selected.get("color", self.default_color_if_unknown)
        if not norm_color:
            norm_color = self.default_color_if_unknown
        color_msg.data = norm_color
        self.color_pub.publish(color_msg)

        self.get_logger().info(
            f"Command='{command}' -> frame={selected['frame_id']}, "
            f"color={color_msg.data}, scene={len(scene)}"
        )

    def build_scene_snapshot(self) -> List[Dict]:
        with self.lock:
            dets = list(self.latest_detections)
            img = None if self.latest_image is None else self.latest_image.copy()

        if not dets:
            return []

        scene = []
        for det in dets:
            color = "unknown"
            if img is not None:
                color = self.estimate_color(img, det)
            scene.append(
                {
                    "frame_id": det["frame_id"],
                    "rank": det["rank"],
                    "x_order": det["rank"],
                    "center_x": round(det["cx"], 2),
                    "color": color,
                }
            )
        return scene

    def estimate_color(self, image_bgr: np.ndarray, det: Dict) -> str:
        h, w = image_bgr.shape[:2]
        x1 = int(max(0, det["cx"] - det["sx"] * 0.45))
        y1 = int(max(0, det["cy"] - det["sy"] * 0.45))
        x2 = int(min(w - 1, det["cx"] + det["sx"] * 0.45))
        y2 = int(min(h - 1, det["cy"] + det["sy"] * 0.45))
        if x2 <= x1 or y2 <= y1:
            return "unknown"
        roi = image_bgr[y1:y2, x1:x2]
        if roi.size == 0:
            return "unknown"

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        best_color = "unknown"
        best_ratio = 0.0
        for color, ranges in self.color_hsv_ranges.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for low, high in ranges:
                mask = cv2.bitwise_or(
                    mask,
                    cv2.inRange(
                        hsv,
                        np.array(low, dtype=np.uint8),
                        np.array(high, dtype=np.uint8),
                    ),
                )
            ratio = float(np.count_nonzero(mask)) / float(mask.size)
            if ratio > best_ratio:
                best_ratio = ratio
                best_color = color
        return best_color if best_ratio >= self.min_color_ratio else "unknown"

    def parse_with_fallback(self, command: str) -> Dict:
        cmd = command.strip().lower()
        parsed: Dict = {"intent": "pick", "color": None, "position": None, "index": None, "frame_id": None}

        for key in ["red", "green", "blue", "yellow", "orange", "红色", "红", "绿色", "绿", "蓝色", "蓝", "黄色", "黄", "橙色", "橙"]:
            if key in command:
                parsed["color"] = normalize_color_name(key)
                break

        if "最左" in command or "leftmost" in cmd:
            parsed["position"] = "leftmost"
        elif "最右" in command or "rightmost" in cmd:
            parsed["position"] = "rightmost"
        elif "中间" in command or "middle" in cmd or "center" in cmd:
            parsed["position"] = "middle"

        frame_match = re.search(r"cube\s*([1-9][0-9]*)", cmd)
        if frame_match:
            parsed["frame_id"] = f"cube{int(frame_match.group(1))}"

        idx_match = re.search(r"第\s*([1-9][0-9]*)\s*个", command)
        if idx_match:
            parsed["index"] = int(idx_match.group(1))
        elif frame_match:
            parsed["index"] = int(frame_match.group(1))
        return parsed

    def parse_with_llm(self, command: str, scene: List[Dict]) -> Optional[Dict]:
        prompt = (
            "Extract robot grasp intent from user command and scene.\n"
            "Return strict JSON only with keys: intent,color,position,index,frame_id.\n"
            "Allowed values:\n"
            "intent: pick|none\n"
            "color: red|green|blue|yellow|orange|all|null\n"
            "position: leftmost|rightmost|middle|any|null\n"
            "index: integer or null\n"
            "frame_id: cubeN or null.\n"
        )

        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"command": command, "scene": scene},
                        ensure_ascii=False,
                    ),
                },
            ],
        }

        req = urllib.request.Request(
            f"{self.api_base}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.URLError as exc:
            self.get_logger().warn(f"OpenAI request failed: {exc}")
            return None
        except Exception as exc:
            self.get_logger().warn(f"OpenAI request error: {exc}")
            return None

        try:
            data = json.loads(body)
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                return None
            return parsed
        except Exception as exc:
            self.get_logger().warn(f"Failed to parse OpenAI response: {exc}")
            return None

    def resolve_target(self, parsed: Dict, scene: List[Dict]) -> Optional[Dict]:
        if not scene:
            return None

        frame_id = str(parsed.get("frame_id") or "").strip()
        if frame_id:
            for obj in scene:
                if obj["frame_id"] == frame_id:
                    return obj

        candidates = list(scene)
        color = normalize_color_name(parsed.get("color"))
        if color and color != "all":
            filtered = [obj for obj in candidates if obj.get("color") == color]
            if filtered:
                candidates = filtered

        position = normalize_position_name(parsed.get("position"))
        index = parsed.get("index")
        if isinstance(index, (int, float)):
            idx = int(index)
            if idx >= 1:
                for obj in candidates:
                    if obj["rank"] == idx:
                        return obj

        if position == "leftmost":
            return min(candidates, key=lambda x: x["center_x"])
        if position == "rightmost":
            return max(candidates, key=lambda x: x["center_x"])
        if position == "middle":
            ordered = sorted(candidates, key=lambda x: x["center_x"])
            return ordered[len(ordered) // 2]
        return sorted(candidates, key=lambda x: x["center_x"])[0]


def main(args=None) -> None:
    rclpy.init(args=args)
    node = OpenAISelector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
