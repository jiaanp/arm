import rclpy
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import String
from tf2_ros import Buffer, TransformException, TransformListener
from vision_msgs.msg import Detection2DArray

import struct
import threading

class PointCloudProcessor(Node):
    def __init__(self):
        super().__init__('point_cloud_processor')
        self.declare_parameter('x_min_ratio', 0.3)
        self.declare_parameter('x_max_ratio', 0.7)
        self.declare_parameter('y_min_ratio', 0.3)
        self.declare_parameter('y_max_ratio', 0.7)
        self.declare_parameter('input_cloud_topic', '/depth/points')
        self.declare_parameter('detection_topic', '/detection')
        self.declare_parameter('target_frame_topic', '/grasp_target_frame')
        self.declare_parameter('exclude_target_only', False)
        self.declare_parameter('exclude_all_if_no_target', True)
        self.declare_parameter('exclude_bbox_margin_px', 14)
        self.declare_parameter('detection_max_age_sec', 2.0)
        self.declare_parameter('exclude_box_size_x', 0.12)
        self.declare_parameter('exclude_box_size_y', 0.12)
        self.declare_parameter('exclude_box_size_z', 0.12)
        self.declare_parameter('detection_label_filter', 'cube')
        self.declare_parameter('retain_last_nonempty_detections', True)
        self.declare_parameter('exclude_wrist_camera', True)
        self.declare_parameter('wrist_camera_frame', 'wrist_camera_link')
        self.declare_parameter('wrist_camera_box_size_x', 0.18)
        self.declare_parameter('wrist_camera_box_size_y', 0.16)
        self.declare_parameter('wrist_camera_box_size_z', 0.16)

        self._lock = threading.Lock()
        self._latest_detections = []
        self._latest_detection_stamp_sec = 0.0
        self._target_frame = ''
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

        self.subscription = self.create_subscription(
            PointCloud2,
            self.get_parameter('input_cloud_topic').value,
            self.listener_callback,
            10)
        self.detection_subscription = self.create_subscription(
            Detection2DArray,
            self.get_parameter('detection_topic').value,
            self.detection_callback,
            10)
        self.target_frame_subscription = self.create_subscription(
            String,
            self.get_parameter('target_frame_topic').value,
            self.target_frame_callback,
            10)
        self.publisher_ = self.create_publisher(PointCloud2, '/depth/points_filtered', 10)

    def detection_callback(self, msg):
        label_filter = str(self.get_parameter('detection_label_filter').value).strip()
        retain_last = bool(self.get_parameter('retain_last_nonempty_detections').value)
        detections = []
        for idx, det in enumerate(msg.detections, start=1):
            if label_filter and det.id != label_filter:
                continue
            detections.append({
                'frame_id': f'cube{idx}',
                'label': det.id,
                'cx': float(det.bbox.center.position.x),
                'cy': float(det.bbox.center.position.y),
                'sx': float(det.bbox.size_x),
                'sy': float(det.bbox.size_y),
            })

        stamp_sec = float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec) * 1e-9
        if stamp_sec <= 0.0:
            stamp_sec = self.get_clock().now().nanoseconds * 1e-9

        with self._lock:
            if retain_last and not detections:
                return
            self._latest_detections = detections
            self._latest_detection_stamp_sec = stamp_sec

    def target_frame_callback(self, msg):
        with self._lock:
            self._target_frame = msg.data.strip()

    def _get_detections_to_exclude(self):
        max_age_sec = float(self.get_parameter('detection_max_age_sec').value)
        exclude_target_only = bool(self.get_parameter('exclude_target_only').value)
        exclude_all_if_no_target = bool(self.get_parameter('exclude_all_if_no_target').value)

        with self._lock:
            detections = list(self._latest_detections)
            target_frame = self._target_frame
            stamp_sec = self._latest_detection_stamp_sec

        if not detections:
            return []

        now_sec = self.get_clock().now().nanoseconds * 1e-9
        if max_age_sec > 0.0 and stamp_sec > 0.0 and (now_sec - stamp_sec) > max_age_sec:
            return []

        if exclude_target_only and target_frame:
            return [det for det in detections if det['frame_id'] == target_frame]

        if exclude_all_if_no_target:
            return detections

        return []

    def _clear_detected_regions(self, data, msg, crop_x_start, crop_y_start, new_width, new_height):
        detections = self._get_detections_to_exclude()
        if not detections:
            return

        x_offset = y_offset = z_offset = None
        for field in msg.fields:
            if field.name == 'x':
                x_offset = field.offset
            elif field.name == 'y':
                y_offset = field.offset
            elif field.name == 'z':
                z_offset = field.offset

        if x_offset is None or y_offset is None or z_offset is None:
            self.get_logger().warn('Point cloud fields do not contain x/y/z, skip target clearing')
            return

        margin = int(self.get_parameter('exclude_bbox_margin_px').value)
        fmt = '>f' if msg.is_bigendian else '<f'
        nan_value = float('nan')

        for det in detections:
            x1 = max(0, int(det['cx'] - det['sx'] * 0.5) - margin)
            y1 = max(0, int(det['cy'] - det['sy'] * 0.5) - margin)
            x2 = min(msg.width - 1, int(det['cx'] + det['sx'] * 0.5) + margin)
            y2 = min(msg.height - 1, int(det['cy'] + det['sy'] * 0.5) + margin)

            local_x1 = max(0, x1 - crop_x_start)
            local_y1 = max(0, y1 - crop_y_start)
            local_x2 = min(new_width - 1, x2 - crop_x_start)
            local_y2 = min(new_height - 1, y2 - crop_y_start)

            if local_x1 > local_x2 or local_y1 > local_y2:
                continue

            for row in range(local_y1, local_y2 + 1):
                row_offset = row * new_width * msg.point_step
                for col in range(local_x1, local_x2 + 1):
                    point_offset = row_offset + col * msg.point_step
                    struct.pack_into(fmt, data, point_offset + x_offset, nan_value)
                    struct.pack_into(fmt, data, point_offset + y_offset, nan_value)
                    struct.pack_into(fmt, data, point_offset + z_offset, nan_value)

    def _get_tf_exclusion_boxes(self, cloud_frame):
        detections = self._get_detections_to_exclude()

        boxes = []
        if detections:
            half_x = float(self.get_parameter('exclude_box_size_x').value) * 0.5
            half_y = float(self.get_parameter('exclude_box_size_y').value) * 0.5
            half_z = float(self.get_parameter('exclude_box_size_z').value) * 0.5

            for det in detections:
                try:
                    transform = self._tf_buffer.lookup_transform(
                        cloud_frame, det['frame_id'], Time())
                except TransformException:
                    continue

                center = transform.transform.translation
                boxes.append((
                    center.x - half_x, center.x + half_x,
                    center.y - half_y, center.y + half_y,
                    center.z - half_z, center.z + half_z,
                ))

        if bool(self.get_parameter('exclude_wrist_camera').value):
            wrist_frame = str(self.get_parameter('wrist_camera_frame').value).strip()
            if wrist_frame:
                try:
                    transform = self._tf_buffer.lookup_transform(cloud_frame, wrist_frame, Time())
                    center = transform.transform.translation
                    half_x = float(self.get_parameter('wrist_camera_box_size_x').value) * 0.5
                    half_y = float(self.get_parameter('wrist_camera_box_size_y').value) * 0.5
                    half_z = float(self.get_parameter('wrist_camera_box_size_z').value) * 0.5
                    boxes.append((
                        center.x - half_x, center.x + half_x,
                        center.y - half_y, center.y + half_y,
                        center.z - half_z, center.z + half_z,
                    ))
                except TransformException:
                    pass

        return boxes

    def _clear_detected_regions_by_tf(self, data, msg, new_width, new_height):
        boxes = self._get_tf_exclusion_boxes(msg.header.frame_id)
        if not boxes:
            return

        x_offset = y_offset = z_offset = None
        for field in msg.fields:
            if field.name == 'x':
                x_offset = field.offset
            elif field.name == 'y':
                y_offset = field.offset
            elif field.name == 'z':
                z_offset = field.offset

        if x_offset is None or y_offset is None or z_offset is None:
            return

        fmt = '>f' if msg.is_bigendian else '<f'
        nan_value = float('nan')

        for row in range(new_height):
            row_offset = row * new_width * msg.point_step
            for col in range(new_width):
                point_offset = row_offset + col * msg.point_step
                x = struct.unpack_from(fmt, data, point_offset + x_offset)[0]
                y = struct.unpack_from(fmt, data, point_offset + y_offset)[0]
                z = struct.unpack_from(fmt, data, point_offset + z_offset)[0]

                if not (x == x and y == y and z == z):
                    continue

                for xmin, xmax, ymin, ymax, zmin, zmax in boxes:
                    if xmin <= x <= xmax and ymin <= y <= ymax and zmin <= z <= zmax:
                        struct.pack_into(fmt, data, point_offset + x_offset, nan_value)
                        struct.pack_into(fmt, data, point_offset + y_offset, nan_value)
                        struct.pack_into(fmt, data, point_offset + z_offset, nan_value)
                        break

    def listener_callback(self, msg):
        x_min_ratio = float(self.get_parameter('x_min_ratio').value)
        x_max_ratio = float(self.get_parameter('x_max_ratio').value)
        y_min_ratio = float(self.get_parameter('y_min_ratio').value)
        y_max_ratio = float(self.get_parameter('y_max_ratio').value)

        x_min_ratio = max(0.0, min(x_min_ratio, 1.0))
        x_max_ratio = max(0.0, min(x_max_ratio, 1.0))
        y_min_ratio = max(0.0, min(y_min_ratio, 1.0))
        y_max_ratio = max(0.0, min(y_max_ratio, 1.0))

        if x_min_ratio >= x_max_ratio or y_min_ratio >= y_max_ratio:
            self.get_logger().warn('Invalid crop ratios, skip publishing')
            return

        if msg.height > 1:  # 有组织的点云
            x_start = int(msg.width * x_min_ratio)
            x_end = int(msg.width * x_max_ratio)
            y_start = int(msg.height * y_min_ratio)
            y_end = int(msg.height * y_max_ratio)

            new_width = x_end - x_start
            new_height = y_end - y_start
            if new_width < 1 or new_height < 1:
                self.get_logger().info('Cropped region too small, not publishing')
                return
            new_row_step = new_width * msg.point_step
            new_data = bytearray()
            for row in range(y_start, y_end):
                row_start = row * msg.row_step + x_start * msg.point_step
                row_end = row_start + new_row_step
                new_data.extend(msg.data[row_start:row_end])

            self._clear_detected_regions(new_data, msg, x_start, y_start, new_width, new_height)
            self._clear_detected_regions_by_tf(new_data, msg, new_width, new_height)
            
            # 创建新的 PointCloud2 消息
            new_msg = PointCloud2()
            new_msg.header = msg.header
            new_msg.height = new_height
            new_msg.width = new_width
            new_msg.fields = msg.fields
            new_msg.is_bigendian = msg.is_bigendian
            new_msg.point_step = msg.point_step
            new_msg.row_step = new_row_step
            new_msg.data = bytes(new_data)
            new_msg.is_dense = False

            # 发布过滤后的点云
            self.publisher_.publish(new_msg)
        
        elif msg.height == 1:  # 无组织的点云
            x_start = int(msg.width * x_min_ratio)
            x_end = int(msg.width * x_max_ratio)
            new_width = x_end - x_start
            if new_width < 1:
                self.get_logger().info('New width too small, not publishing')
                return
            start = x_start * msg.point_step
            data_size = new_width * msg.point_step
            new_data = msg.data[start:start + data_size]
            
            # 创建新的 PointCloud2 消息
            new_msg = PointCloud2()
            new_msg.header = msg.header
            new_msg.height = 1
            new_msg.width = new_width
            new_msg.fields = msg.fields
            new_msg.is_bigendian = msg.is_bigendian
            new_msg.point_step = msg.point_step
            new_msg.row_step = new_width * msg.point_step
            new_msg.data = new_data
            new_msg.is_dense = msg.is_dense
            
            # 发布过滤后的点云
            self.publisher_.publish(new_msg)
        
        else:
            self.get_logger().warn('Point cloud has height <1, cannot process')

def main(args=None):
    rclpy.init(args=args)
    point_cloud_processor = PointCloudProcessor()
    rclpy.spin(point_cloud_processor)
    point_cloud_processor.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
