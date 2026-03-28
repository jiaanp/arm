from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.substitutions import FindPackageShare


def launch_setup(context, *args, **kwargs):
    enable_wrist_yaw_estimator = LaunchConfiguration("enable_wrist_yaw_estimator")
    wrist_yaw_image_topic = LaunchConfiguration("wrist_yaw_image_topic")
    wrist_yaw_debug_image_topic = LaunchConfiguration("wrist_yaw_debug_image_topic")
    wrist_yaw_topic = LaunchConfiguration("wrist_yaw_topic")
    wrist_yaw_raw_topic = LaunchConfiguration("wrist_yaw_raw_topic")
    wrist_yaw_delta_topic = LaunchConfiguration("wrist_yaw_delta_topic")
    wrist_yaw_target_color = LaunchConfiguration("wrist_yaw_target_color")
    wrist_yaw_target_color_topic = LaunchConfiguration("wrist_yaw_target_color_topic")
    wrist_yaw_base_frame = LaunchConfiguration("wrist_yaw_base_frame")
    wrist_yaw_camera_frame = LaunchConfiguration("wrist_yaw_camera_frame")
    wrist_yaw_camera_offset_rad = LaunchConfiguration("wrist_yaw_camera_offset_rad")
    wrist_yaw_object_to_gripper_offset_rad = LaunchConfiguration("wrist_yaw_object_to_gripper_offset_rad")
    wrist_yaw_resolve_square_symmetry = LaunchConfiguration("wrist_yaw_resolve_square_symmetry")
    wrist_yaw_symmetry_step_deg = LaunchConfiguration("wrist_yaw_symmetry_step_deg")
    wrist_yaw_symmetry_half_window = LaunchConfiguration("wrist_yaw_symmetry_half_window")
    wrist_yaw_reference_use_camera_yaw = LaunchConfiguration("wrist_yaw_reference_use_camera_yaw")
    wrist_yaw_reference_yaw_rad = LaunchConfiguration("wrist_yaw_reference_yaw_rad")
    wrist_yaw_reference_yaw_offset_rad = LaunchConfiguration("wrist_yaw_reference_yaw_offset_rad")
    wrist_yaw_invert_delta = LaunchConfiguration("wrist_yaw_invert_delta")
    wrist_yaw_min_contour_area = LaunchConfiguration("wrist_yaw_min_contour_area")
    wrist_yaw_max_contour_area = LaunchConfiguration("wrist_yaw_max_contour_area")
    wrist_yaw_center_weight = LaunchConfiguration("wrist_yaw_center_weight")
    wrist_yaw_publish_debug_image = LaunchConfiguration("wrist_yaw_publish_debug_image")
    enable_openai_selector = LaunchConfiguration("enable_openai_selector")
    grasp_command_topic = LaunchConfiguration("grasp_command_topic")
    grasp_target_frame_topic = LaunchConfiguration("grasp_target_frame_topic")
    openai_target_color_topic = LaunchConfiguration("openai_target_color_topic")
    openai_scene_detection_topic = LaunchConfiguration("openai_scene_detection_topic")
    openai_scene_image_topic = LaunchConfiguration("openai_scene_image_topic")
    openai_use_llm = LaunchConfiguration("openai_use_llm")
    openai_model = LaunchConfiguration("openai_model")
    openai_api_base = LaunchConfiguration("openai_api_base")
    openai_timeout_sec = LaunchConfiguration("openai_timeout_sec")
    openai_fallback_only = LaunchConfiguration("openai_fallback_only")
    # load urdf, launch gazebo
    dual_ur5e_gripper_control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare("ur5e_gripper_moveit_config"), "/launch", "/ur5e_gripper_sim_control.launch.py"]
        ),
        launch_arguments={
            "launch_rviz": "true",
        }.items(),
    )

    # load moveit config
    dual_ur5e_gripper_moveit_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare("ur5e_gripper_moveit_config"), "/launch", "/ur5e_gripper_moveit.launch.py"]
        ),
        launch_arguments={
            "use_sim_time": "true",
        }.items(),
    )

    # depth image registered (align to color image)
    register_depth_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare("vision"), "/launch", "/register_depth.launch.py"]
        ),
    )

    vision_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare("vision"), "/launch", "/seg_and_det.launch.py"]
        ),
        launch_arguments={
            "enable_wrist_yaw_estimator": enable_wrist_yaw_estimator,
            "wrist_yaw_image_topic": wrist_yaw_image_topic,
            "wrist_yaw_debug_image_topic": wrist_yaw_debug_image_topic,
            "wrist_yaw_topic": wrist_yaw_topic,
            "wrist_yaw_raw_topic": wrist_yaw_raw_topic,
            "wrist_yaw_delta_topic": wrist_yaw_delta_topic,
            "wrist_yaw_target_color": wrist_yaw_target_color,
            "wrist_yaw_target_color_topic": wrist_yaw_target_color_topic,
            "wrist_yaw_base_frame": wrist_yaw_base_frame,
            "wrist_yaw_camera_frame": wrist_yaw_camera_frame,
            "wrist_yaw_camera_offset_rad": wrist_yaw_camera_offset_rad,
            "wrist_yaw_object_to_gripper_offset_rad": wrist_yaw_object_to_gripper_offset_rad,
            "wrist_yaw_resolve_square_symmetry": wrist_yaw_resolve_square_symmetry,
            "wrist_yaw_symmetry_step_deg": wrist_yaw_symmetry_step_deg,
            "wrist_yaw_symmetry_half_window": wrist_yaw_symmetry_half_window,
            "wrist_yaw_reference_use_camera_yaw": wrist_yaw_reference_use_camera_yaw,
            "wrist_yaw_reference_yaw_rad": wrist_yaw_reference_yaw_rad,
            "wrist_yaw_reference_yaw_offset_rad": wrist_yaw_reference_yaw_offset_rad,
            "wrist_yaw_invert_delta": wrist_yaw_invert_delta,
            "wrist_yaw_min_contour_area": wrist_yaw_min_contour_area,
            "wrist_yaw_max_contour_area": wrist_yaw_max_contour_area,
            "wrist_yaw_center_weight": wrist_yaw_center_weight,
            "wrist_yaw_publish_debug_image": wrist_yaw_publish_debug_image,
            "enable_openai_selector": enable_openai_selector,
            "grasp_command_topic": grasp_command_topic,
            "grasp_target_frame_topic": grasp_target_frame_topic,
            "openai_target_color_topic": openai_target_color_topic,
            "openai_scene_detection_topic": openai_scene_detection_topic,
            "openai_scene_image_topic": openai_scene_image_topic,
            "openai_use_llm": openai_use_llm,
            "openai_model": openai_model,
            "openai_api_base": openai_api_base,
            "openai_timeout_sec": openai_timeout_sec,
            "openai_fallback_only": openai_fallback_only,
        }.items(),
    )
    nodes_to_launch = [
        dual_ur5e_gripper_control_launch,
        dual_ur5e_gripper_moveit_launch,
        register_depth_launch,
        vision_launch,
    ]

    return nodes_to_launch


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument("enable_wrist_yaw_estimator", default_value="true"),
        DeclareLaunchArgument("wrist_yaw_image_topic", default_value="/wrist_camera/color/image_raw"),
        DeclareLaunchArgument("wrist_yaw_debug_image_topic", default_value="/wrist_yaw_debug_image"),
        DeclareLaunchArgument("wrist_yaw_topic", default_value="/wrist_target_yaw"),
        DeclareLaunchArgument("wrist_yaw_raw_topic", default_value="/wrist_target_yaw_raw"),
        DeclareLaunchArgument("wrist_yaw_delta_topic", default_value="/wrist_target_yaw_delta"),
        DeclareLaunchArgument("wrist_yaw_target_color", default_value="all"),
        DeclareLaunchArgument("wrist_yaw_target_color_topic", default_value="/wrist_target_color"),
        DeclareLaunchArgument("wrist_yaw_base_frame", default_value="base_link"),
        DeclareLaunchArgument("wrist_yaw_camera_frame", default_value="wrist_camera_color_optical_frame"),
        DeclareLaunchArgument("wrist_yaw_camera_offset_rad", default_value="0.0"),
        DeclareLaunchArgument("wrist_yaw_object_to_gripper_offset_rad", default_value="0.0"),
        DeclareLaunchArgument("wrist_yaw_resolve_square_symmetry", default_value="true"),
        DeclareLaunchArgument("wrist_yaw_symmetry_step_deg", default_value="90.0"),
        DeclareLaunchArgument("wrist_yaw_symmetry_half_window", default_value="2"),
        DeclareLaunchArgument("wrist_yaw_reference_use_camera_yaw", default_value="true"),
        DeclareLaunchArgument("wrist_yaw_reference_yaw_rad", default_value="0.0"),
        DeclareLaunchArgument("wrist_yaw_reference_yaw_offset_rad", default_value="0.0"),
        DeclareLaunchArgument("wrist_yaw_invert_delta", default_value="true"),
        DeclareLaunchArgument("wrist_yaw_min_contour_area", default_value="800.0"),
        DeclareLaunchArgument("wrist_yaw_max_contour_area", default_value="160000.0"),
        DeclareLaunchArgument("wrist_yaw_center_weight", default_value="0.35"),
        DeclareLaunchArgument("wrist_yaw_publish_debug_image", default_value="true"),
        DeclareLaunchArgument("enable_openai_selector", default_value="true"),
        DeclareLaunchArgument("grasp_command_topic", default_value="/grasp_command_text"),
        DeclareLaunchArgument("grasp_target_frame_topic", default_value="/grasp_target_frame"),
        DeclareLaunchArgument("openai_target_color_topic", default_value="/wrist_target_color"),
        DeclareLaunchArgument("openai_scene_detection_topic", default_value="/detection"),
        DeclareLaunchArgument("openai_scene_image_topic", default_value="/color/image_raw"),
        DeclareLaunchArgument("openai_use_llm", default_value="true"),
        DeclareLaunchArgument("openai_model", default_value="gpt-4.1-mini"),
        DeclareLaunchArgument("openai_api_base", default_value="https://api.openai.com/v1"),
        DeclareLaunchArgument("openai_timeout_sec", default_value="8.0"),
        DeclareLaunchArgument("openai_fallback_only", default_value="false"),
    ]

    return LaunchDescription(declared_arguments + [OpaqueFunction(function=launch_setup)])
