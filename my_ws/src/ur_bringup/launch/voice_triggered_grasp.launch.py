from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration


def launch_setup(context, *args, **kwargs):
    cmd = [
        'python3', '-m', 'ur_bringup.voice_grasp_session',
        '--ros-args',
        '-p', f"request_topic:={LaunchConfiguration('request_topic').perform(context)}",
        '-p', f"control_topic:={LaunchConfiguration('control_topic').perform(context)}",
        '-p', f"grasp_command_topic:={LaunchConfiguration('grasp_command_topic').perform(context)}",
        '-p', f"target_frame_topic:={LaunchConfiguration('target_frame_topic').perform(context)}",
        '-p', f"wrist_yaw_topic:={LaunchConfiguration('wrist_yaw_topic').perform(context)}",
        '-p', f"wait_for_target_frame_sec:={LaunchConfiguration('wait_for_target_frame_sec').perform(context)}",
        '-p', f"grasp_start_delay_sec:={LaunchConfiguration('grasp_start_delay_sec').perform(context)}",
        '-p', f"enable_wrist_yaw_refine:={LaunchConfiguration('enable_wrist_yaw_refine').perform(context)}",
        '-p', f"grasp_close_position:={LaunchConfiguration('grasp_close_position').perform(context)}",
        '-p', f"grasp_settle_time_sec:={LaunchConfiguration('grasp_settle_time_sec').perform(context)}",
        '-p', f"grasp_x_offset:={LaunchConfiguration('grasp_x_offset').perform(context)}",
        '-p', f"grasp_y_offset:={LaunchConfiguration('grasp_y_offset').perform(context)}",
        '-p', f"grasp_z_offset:={LaunchConfiguration('grasp_z_offset').perform(context)}",
        '-p', f"post_grasp_lift_height:={LaunchConfiguration('post_grasp_lift_height').perform(context)}",
        '-p', f"pre_grasp_hover_distance:={LaunchConfiguration('pre_grasp_hover_distance').perform(context)}",
        '-p', f"pre_grasp_pause_sec:={LaunchConfiguration('pre_grasp_pause_sec').perform(context)}",
        '-p', f"wrist_yaw_is_delta:={LaunchConfiguration('wrist_yaw_is_delta').perform(context)}",
        '-p', f"wrist_yaw_max_age_sec:={LaunchConfiguration('wrist_yaw_max_age_sec').perform(context)}",
        '-p', f"wrist_yaw_min_change_rad:={LaunchConfiguration('wrist_yaw_min_change_rad').perform(context)}",
        '-p', f"wrist_yaw_settle_time_sec:={LaunchConfiguration('wrist_yaw_settle_time_sec').perform(context)}",
    ]
    return [ExecuteProcess(cmd=cmd, output='screen')]


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument("request_topic", default_value="/voice_grasp_request"),
        DeclareLaunchArgument("control_topic", default_value="/grasp_session_control"),
        DeclareLaunchArgument("grasp_command_topic", default_value="/grasp_command_text"),
        DeclareLaunchArgument("target_frame_topic", default_value="/grasp_target_frame"),
        DeclareLaunchArgument("wrist_yaw_topic", default_value="/wrist_target_yaw_delta"),
        DeclareLaunchArgument("wait_for_target_frame_sec", default_value="600.0"),
        DeclareLaunchArgument("grasp_start_delay_sec", default_value="1.0"),
        DeclareLaunchArgument("enable_wrist_yaw_refine", default_value="true"),
        DeclareLaunchArgument("grasp_close_position", default_value="0.36"),
        DeclareLaunchArgument("grasp_settle_time_sec", default_value="1.50"),
        DeclareLaunchArgument("grasp_x_offset", default_value="-0.012"),
        DeclareLaunchArgument("grasp_y_offset", default_value="0.010"),
        DeclareLaunchArgument("grasp_z_offset", default_value="0.140"),
        DeclareLaunchArgument("post_grasp_lift_height", default_value="0.10"),
        DeclareLaunchArgument("pre_grasp_hover_distance", default_value="0.08"),
        DeclareLaunchArgument("pre_grasp_pause_sec", default_value="0.30"),
        DeclareLaunchArgument("wrist_yaw_is_delta", default_value="true"),
        DeclareLaunchArgument("wrist_yaw_max_age_sec", default_value="0.60"),
        DeclareLaunchArgument("wrist_yaw_min_change_rad", default_value="0.01"),
        DeclareLaunchArgument("wrist_yaw_settle_time_sec", default_value="0.25"),
    ]
    return LaunchDescription(declared_arguments + [OpaqueFunction(function=launch_setup)])
