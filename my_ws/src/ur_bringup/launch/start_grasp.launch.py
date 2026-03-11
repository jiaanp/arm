import json

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.substitutions import FindPackageShare


def launch_setup(context, *args, **kwargs):
    pre_grasp_hover_distance = LaunchConfiguration("pre_grasp_hover_distance")
    pre_grasp_pause_sec = LaunchConfiguration("pre_grasp_pause_sec")
    grasp_close_position = LaunchConfiguration("grasp_close_position")
    grasp_settle_time_sec = LaunchConfiguration("grasp_settle_time_sec")
    grasp_x_offset = LaunchConfiguration("grasp_x_offset")
    grasp_y_offset = LaunchConfiguration("grasp_y_offset")
    grasp_z_offset = LaunchConfiguration("grasp_z_offset")
    post_grasp_lift_height = LaunchConfiguration("post_grasp_lift_height")
    enable_wrist_yaw_refine = LaunchConfiguration("enable_wrist_yaw_refine")
    wrist_yaw_topic = LaunchConfiguration("wrist_yaw_topic")
    wrist_yaw_is_delta = LaunchConfiguration("wrist_yaw_is_delta")
    wrist_yaw_settle_time_sec = LaunchConfiguration("wrist_yaw_settle_time_sec")
    wrist_yaw_max_age_sec = LaunchConfiguration("wrist_yaw_max_age_sec")
    wrist_yaw_min_change_rad = LaunchConfiguration("wrist_yaw_min_change_rad")
    target_cube_frame = LaunchConfiguration("target_cube_frame")
    target_frame_topic = LaunchConfiguration("target_frame_topic")
    wait_for_target_frame_sec = LaunchConfiguration("wait_for_target_frame_sec")
    grasp_all_if_no_target = LaunchConfiguration("grasp_all_if_no_target")
    grasp_command_text = LaunchConfiguration("grasp_command_text").perform(context).strip()
    command_publish_delay_sec = float(LaunchConfiguration("command_publish_delay_sec").perform(context))
    grasp_start_delay_sec = float(LaunchConfiguration("grasp_start_delay_sec").perform(context))
    grasp_command_topic = LaunchConfiguration("grasp_command_topic").perform(context).strip()

    if grasp_command_text and command_publish_delay_sec <= grasp_start_delay_sec:
        command_publish_delay_sec = grasp_start_delay_sec + 0.5

    grasp_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare("ur5e_gripper_control"), "/launch", "/demo.launch.py"]
        ),
        launch_arguments={
            "pre_grasp_hover_distance": pre_grasp_hover_distance,
            "pre_grasp_pause_sec": pre_grasp_pause_sec,
            "grasp_close_position": grasp_close_position,
            "grasp_settle_time_sec": grasp_settle_time_sec,
            "grasp_x_offset": grasp_x_offset,
            "grasp_y_offset": grasp_y_offset,
            "grasp_z_offset": grasp_z_offset,
            "post_grasp_lift_height": post_grasp_lift_height,
            "enable_wrist_yaw_refine": enable_wrist_yaw_refine,
            "wrist_yaw_topic": wrist_yaw_topic,
            "wrist_yaw_is_delta": wrist_yaw_is_delta,
            "wrist_yaw_settle_time_sec": wrist_yaw_settle_time_sec,
            "wrist_yaw_max_age_sec": wrist_yaw_max_age_sec,
            "wrist_yaw_min_change_rad": wrist_yaw_min_change_rad,
            "target_cube_frame": target_cube_frame,
            "target_frame_topic": target_frame_topic,
            "wait_for_target_frame_sec": wait_for_target_frame_sec,
            "grasp_all_if_no_target": grasp_all_if_no_target,
        }.items(),
    )

    nodes_to_launch = []
    if grasp_command_text and grasp_command_topic:
        command_msg = f"data: {json.dumps(grasp_command_text, ensure_ascii=False)}"
        publish_command = ExecuteProcess(
            cmd=[
                "ros2",
                "topic",
                "pub",
                "--once",
                grasp_command_topic,
                "std_msgs/msg/String",
                command_msg,
            ],
            output="screen",
        )
        nodes_to_launch.append(TimerAction(period=command_publish_delay_sec, actions=[publish_command]))

    nodes_to_launch.append(TimerAction(period=grasp_start_delay_sec, actions=[grasp_launch]))
    return nodes_to_launch


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument("pre_grasp_hover_distance", default_value="0.08"),
        DeclareLaunchArgument("pre_grasp_pause_sec", default_value="0.30"),
        DeclareLaunchArgument("grasp_close_position", default_value="0.36"),
        DeclareLaunchArgument("grasp_settle_time_sec", default_value="1.50"),
        DeclareLaunchArgument("grasp_x_offset", default_value="-0.012"),
        DeclareLaunchArgument("grasp_y_offset", default_value="0.010"),
        DeclareLaunchArgument("grasp_z_offset", default_value="0.140"),
        DeclareLaunchArgument("post_grasp_lift_height", default_value="0.10"),
        DeclareLaunchArgument("enable_wrist_yaw_refine", default_value="true"),
        DeclareLaunchArgument("wrist_yaw_topic", default_value="/wrist_target_yaw_delta"),
        DeclareLaunchArgument("wrist_yaw_is_delta", default_value="true"),
        DeclareLaunchArgument("wrist_yaw_settle_time_sec", default_value="0.25"),
        DeclareLaunchArgument("wrist_yaw_max_age_sec", default_value="0.60"),
        DeclareLaunchArgument("wrist_yaw_min_change_rad", default_value="0.01"),
        DeclareLaunchArgument("target_cube_frame", default_value=""),
        DeclareLaunchArgument("target_frame_topic", default_value="/grasp_target_frame"),
        DeclareLaunchArgument("wait_for_target_frame_sec", default_value="3.0"),
        DeclareLaunchArgument("grasp_all_if_no_target", default_value="true"),
        DeclareLaunchArgument("grasp_command_text", default_value=""),
        DeclareLaunchArgument("grasp_command_topic", default_value="/grasp_command_text"),
        DeclareLaunchArgument("command_publish_delay_sec", default_value="2.50"),
        DeclareLaunchArgument("grasp_start_delay_sec", default_value="1.0"),
    ]

    return LaunchDescription(declared_arguments + [OpaqueFunction(function=launch_setup)])
