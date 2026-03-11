import math
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import Image
from std_msgs.msg import Float64, String
from tf2_ros import Buffer, TransformException, TransformListener


def wrap_to_pi(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def quat_to_yaw(x: float, y: float, z: float, w: float) -> float:
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


class WristYawEstimator(Node):
    def __init__(self) -> None:
        super().__init__("wrist_yaw_estimator")

        self.declare_parameter("image_topic", "/wrist_camera/color/image_raw")
        self.declare_parameter("debug_image_topic", "/wrist_yaw_debug_image")
        self.declare_parameter("yaw_topic", "/wrist_target_yaw")
        self.declare_parameter("raw_topic", "/wrist_target_yaw_raw")
        self.declare_parameter("delta_topic", "/wrist_target_yaw_delta")
        self.declare_parameter("target_color", "red")
        self.declare_parameter("target_color_topic", "/wrist_target_color")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("camera_frame", "wrist_camera_color_optical_frame")
        self.declare_parameter("camera_offset_rad", 0.0)
        self.declare_parameter("object_to_gripper_offset_rad", 0.0)
        self.declare_parameter("resolve_square_symmetry", True)
        self.declare_parameter("symmetry_step_deg", 90.0)
        self.declare_parameter("symmetry_half_window", 2)
        self.declare_parameter("reference_use_camera_yaw", True)
        self.declare_parameter("reference_yaw_rad", 0.0)
        self.declare_parameter("reference_yaw_offset_rad", 0.0)
        self.declare_parameter("invert_delta", True)
        self.declare_parameter("min_contour_area", 800.0)
        self.declare_parameter("max_contour_area", 160000.0)
        self.declare_parameter("center_weight", 0.35)
        self.declare_parameter("publish_debug_image", True)

        self.image_topic = str(self.get_parameter("image_topic").value)
        self.debug_image_topic = str(self.get_parameter("debug_image_topic").value)
        self.yaw_topic = str(self.get_parameter("yaw_topic").value)
        self.raw_topic = str(self.get_parameter("raw_topic").value)
        self.delta_topic = str(self.get_parameter("delta_topic").value)
        self.target_color = str(self.get_parameter("target_color").value).strip().lower()
        self.target_color_topic = str(self.get_parameter("target_color_topic").value).strip()
        self.base_frame = str(self.get_parameter("base_frame").value)
        self.camera_frame = str(self.get_parameter("camera_frame").value)
        self.camera_offset_rad = float(self.get_parameter("camera_offset_rad").value)
        self.object_to_gripper_offset_rad = float(self.get_parameter("object_to_gripper_offset_rad").value)
        self.resolve_square_symmetry = bool(self.get_parameter("resolve_square_symmetry").value)
        self.symmetry_step_rad = math.radians(float(self.get_parameter("symmetry_step_deg").value))
        self.symmetry_half_window = int(self.get_parameter("symmetry_half_window").value)
        self.reference_use_camera_yaw = bool(self.get_parameter("reference_use_camera_yaw").value)
        self.reference_yaw_rad = float(self.get_parameter("reference_yaw_rad").value)
        self.reference_yaw_offset_rad = float(self.get_parameter("reference_yaw_offset_rad").value)
        self.invert_delta = bool(self.get_parameter("invert_delta").value)
        self.min_contour_area = float(self.get_parameter("min_contour_area").value)
        self.max_contour_area = float(self.get_parameter("max_contour_area").value)
        self.center_weight = float(self.get_parameter("center_weight").value)
        self.publish_debug_image = bool(self.get_parameter("publish_debug_image").value)

        self.bridge = CvBridge()
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.raw_pub = self.create_publisher(Float64, self.raw_topic, 10)
        self.yaw_pub = self.create_publisher(Float64, self.yaw_topic, 10)
        self.delta_pub = self.create_publisher(Float64, self.delta_topic, 10)
        self.debug_pub = self.create_publisher(Image, self.debug_image_topic, 10)

        self.create_subscription(Image, self.image_topic, self.image_callback, 10)
        if self.target_color_topic:
            self.create_subscription(String, self.target_color_topic, self.target_color_callback, 10)

        self.color_ranges = self.build_color_ranges()
        self.last_log_ns = 0

        self.get_logger().info(
            "Wrist yaw estimator started. "
            f"image_topic={self.image_topic}, yaw_topic={self.yaw_topic}, "
            f"raw_topic={self.raw_topic}, delta_topic={self.delta_topic}"
        )

    @staticmethod
    def build_color_ranges() -> Dict[str, List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]]:
        return {
            "red": [((0, 80, 50), (10, 255, 255)), ((170, 80, 50), (180, 255, 255))],
            "green": [((35, 60, 40), (90, 255, 255))],
            "blue": [((95, 80, 40), (135, 255, 255))],
            "yellow": [((18, 80, 80), (35, 255, 255))],
            "orange": [((8, 80, 80), (20, 255, 255))],
        }

    def target_color_callback(self, msg: String) -> None:
        value = msg.data.strip().lower()
        if value:
            self.target_color = value

    def get_camera_reference_yaw(self) -> Optional[float]:
        if not self.reference_use_camera_yaw:
            return wrap_to_pi(self.reference_yaw_rad)
        try:
            tf_msg = self.tf_buffer.lookup_transform(
                self.base_frame,
                self.camera_frame,
                Time(),
            )
        except TransformException as exc:
            self.get_logger().debug(f"TF lookup failed ({self.base_frame} <- {self.camera_frame}): {exc}")
            return None

        q = tf_msg.transform.rotation
        camera_yaw = quat_to_yaw(q.x, q.y, q.z, q.w)
        return wrap_to_pi(camera_yaw + self.reference_yaw_offset_rad)

    def build_color_mask(self, hsv: np.ndarray, color: str) -> np.ndarray:
        ranges = self.color_ranges.get(color, [])
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for low, high in ranges:
            mask = cv2.bitwise_or(mask, cv2.inRange(hsv, np.array(low, dtype=np.uint8), np.array(high, dtype=np.uint8)))
        return mask

    def detect_target_rect(self, bgr: np.ndarray, target_color: str):
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

        if target_color == "all":
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for color_name in self.color_ranges:
                mask = cv2.bitwise_or(mask, self.build_color_mask(hsv, color_name))
        else:
            mask = self.build_color_mask(hsv, target_color)
            if not np.any(mask):
                # fallback to all colors when target color is unknown or absent
                all_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
                for color_name in self.color_ranges:
                    all_mask = cv2.bitwise_or(all_mask, self.build_color_mask(hsv, color_name))
                mask = all_mask

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        h, w = mask.shape[:2]
        cx_ref = w * 0.5
        cy_ref = h * 0.5
        best = None
        best_score = -1e18

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_contour_area or area > self.max_contour_area:
                continue
            m = cv2.moments(contour)
            if m["m00"] <= 1e-6:
                continue
            cx = m["m10"] / m["m00"]
            cy = m["m01"] / m["m00"]
            dist2 = (cx - cx_ref) ** 2 + (cy - cy_ref) ** 2
            score = area - self.center_weight * dist2
            if score > best_score:
                best_score = score
                best = contour

        if best is None:
            return None

        rect = cv2.minAreaRect(best)
        return rect, mask, best

    def normalize_rect_angle_deg(self, rect) -> float:
        (_, _), (w, h), angle = rect
        if w < h:
            angle += 90.0
        # Keep in [-90, 90)
        while angle >= 90.0:
            angle -= 180.0
        while angle < -90.0:
            angle += 180.0
        return angle

    def resolve_symmetry(self, yaw_raw: float, yaw_ref: float) -> float:
        if not self.resolve_square_symmetry:
            return wrap_to_pi(yaw_raw)
        best = wrap_to_pi(yaw_raw)
        best_err = abs(wrap_to_pi(best - yaw_ref))
        for k in range(-self.symmetry_half_window, self.symmetry_half_window + 1):
            cand = wrap_to_pi(yaw_raw + k * self.symmetry_step_rad)
            err = abs(wrap_to_pi(cand - yaw_ref))
            if err < best_err:
                best = cand
                best_err = err
        return best

    def publish_scalar(self, pub, value: float) -> None:
        msg = Float64()
        msg.data = float(value)
        pub.publish(msg)

    def image_callback(self, msg: Image) -> None:
        try:
            bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().error(f"cv_bridge conversion failed: {exc}")
            return

        detection = self.detect_target_rect(bgr, self.target_color)
        if detection is None:
            if self.publish_debug_image:
                debug = bgr.copy()
                cv2.putText(debug, "no target", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                self.debug_pub.publish(self.bridge.cv2_to_imgmsg(debug, encoding="bgr8"))
            return

        rect, _, contour = detection
        img_angle_deg = self.normalize_rect_angle_deg(rect)
        img_angle_rad = math.radians(img_angle_deg)
        raw_yaw = wrap_to_pi(-img_angle_rad + self.camera_offset_rad + self.object_to_gripper_offset_rad)

        yaw_ref = self.get_camera_reference_yaw()
        if yaw_ref is None:
            yaw_ref = wrap_to_pi(self.reference_yaw_rad)
        final_yaw = self.resolve_symmetry(raw_yaw, yaw_ref)
        delta_yaw = wrap_to_pi(final_yaw - yaw_ref)
        if self.invert_delta:
            delta_yaw = wrap_to_pi(-delta_yaw)

        self.publish_scalar(self.raw_pub, raw_yaw)
        self.publish_scalar(self.yaw_pub, final_yaw)
        self.publish_scalar(self.delta_pub, delta_yaw)

        if self.publish_debug_image:
            debug = bgr.copy()
            box = cv2.boxPoints(rect).astype(np.int32)
            cv2.drawContours(debug, [box], 0, (0, 255, 255), 2)
            cv2.drawContours(debug, [contour], -1, (255, 255, 0), 1)
            text = (
                f"img={img_angle_deg:.1f} raw={math.degrees(raw_yaw):.1f} "
                f"final={math.degrees(final_yaw):.1f} delta={math.degrees(delta_yaw):.1f}"
            )
            cv2.putText(debug, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            self.debug_pub.publish(self.bridge.cv2_to_imgmsg(debug, encoding="bgr8"))

        now_ns = self.get_clock().now().nanoseconds
        if now_ns - self.last_log_ns > int(1.0e9):
            self.last_log_ns = now_ns
            self.get_logger().info(
                f"target={self.target_color}, img={img_angle_deg:.2f} deg, "
                f"raw={raw_yaw:.3f} rad, final={final_yaw:.3f} rad, delta={delta_yaw:.3f} rad"
            )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = WristYawEstimator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
