from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.substitutions import FindPackageShare
import json


def launch_setup(context, *args, **kwargs):
    grasp_command_text = LaunchConfiguration('grasp_command_text').perform(context).strip()
    grasp_command_topic = LaunchConfiguration('grasp_command_topic').perform(context).strip()
    grasp_start_delay_sec = float(LaunchConfiguration('grasp_start_delay_sec').perform(context))
    command_publish_delay_sec = grasp_start_delay_sec + 0.5

    grasp_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare('ur5e_pick_place_control'), '/launch', '/pick_place_demo.launch.py']
        ),
        launch_arguments={
            'place_zone': LaunchConfiguration('place_zone'),
            'pre_grasp_hover_distance': LaunchConfiguration('pre_grasp_hover_distance'),
            'pre_grasp_pause_sec': LaunchConfiguration('pre_grasp_pause_sec'),
            'grasp_close_position': LaunchConfiguration('grasp_close_position'),
            'grasp_settle_time_sec': LaunchConfiguration('grasp_settle_time_sec'),
            'grasp_x_offset': LaunchConfiguration('grasp_x_offset'),
            'grasp_y_offset': LaunchConfiguration('grasp_y_offset'),
            'grasp_z_offset': LaunchConfiguration('grasp_z_offset'),
            'post_grasp_lift_height': LaunchConfiguration('post_grasp_lift_height'),
            'place_hover_distance': LaunchConfiguration('place_hover_distance'),
            'place_pause_sec': LaunchConfiguration('place_pause_sec'),
            'enable_wrist_yaw_refine': LaunchConfiguration('enable_wrist_yaw_refine'),
            'wrist_yaw_topic': LaunchConfiguration('wrist_yaw_topic'),
            'wrist_yaw_is_delta': LaunchConfiguration('wrist_yaw_is_delta'),
            'wrist_yaw_settle_time_sec': LaunchConfiguration('wrist_yaw_settle_time_sec'),
            'wrist_yaw_max_age_sec': LaunchConfiguration('wrist_yaw_max_age_sec'),
            'wrist_yaw_min_change_rad': LaunchConfiguration('wrist_yaw_min_change_rad'),
            'target_cube_frame': LaunchConfiguration('target_cube_frame'),
            'target_frame_topic': LaunchConfiguration('target_frame_topic'),
            'wait_for_target_frame_sec': LaunchConfiguration('wait_for_target_frame_sec'),
        }.items(),
    )

    nodes_to_launch = [TimerAction(period=grasp_start_delay_sec, actions=[grasp_launch])]
    if grasp_command_text and grasp_command_topic:
        command_msg = f'data: {json.dumps(grasp_command_text, ensure_ascii=False)}'
        publish_command = ExecuteProcess(
            cmd=['ros2', 'topic', 'pub', '--once', grasp_command_topic, 'std_msgs/msg/String', command_msg],
            output='screen',
        )
        nodes_to_launch.append(TimerAction(period=command_publish_delay_sec, actions=[publish_command]))
    return nodes_to_launch


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument('grasp_command_text', default_value=''),
        DeclareLaunchArgument('grasp_command_topic', default_value='/grasp_command_text'),
        DeclareLaunchArgument('grasp_start_delay_sec', default_value='1.0'),
        DeclareLaunchArgument('place_zone', default_value='middle'),
        DeclareLaunchArgument('target_cube_frame', default_value=''),
        DeclareLaunchArgument('target_frame_topic', default_value='/grasp_target_frame'),
        DeclareLaunchArgument('wait_for_target_frame_sec', default_value='3.0'),
        DeclareLaunchArgument('pre_grasp_hover_distance', default_value='0.08'),
        DeclareLaunchArgument('pre_grasp_pause_sec', default_value='0.30'),
        DeclareLaunchArgument('grasp_close_position', default_value='0.36'),
        DeclareLaunchArgument('grasp_settle_time_sec', default_value='1.50'),
        DeclareLaunchArgument('grasp_x_offset', default_value='-0.012'),
        DeclareLaunchArgument('grasp_y_offset', default_value='0.010'),
        DeclareLaunchArgument('grasp_z_offset', default_value='0.140'),
        DeclareLaunchArgument('post_grasp_lift_height', default_value='0.10'),
        DeclareLaunchArgument('place_hover_distance', default_value='0.08'),
        DeclareLaunchArgument('place_pause_sec', default_value='0.30'),
        DeclareLaunchArgument('enable_wrist_yaw_refine', default_value='true'),
        DeclareLaunchArgument('wrist_yaw_topic', default_value='/wrist_target_yaw_delta'),
        DeclareLaunchArgument('wrist_yaw_is_delta', default_value='true'),
        DeclareLaunchArgument('wrist_yaw_settle_time_sec', default_value='0.25'),
        DeclareLaunchArgument('wrist_yaw_max_age_sec', default_value='0.60'),
        DeclareLaunchArgument('wrist_yaw_min_change_rad', default_value='0.01'),
    ]
    return LaunchDescription(declared_arguments + [OpaqueFunction(function=launch_setup)])
