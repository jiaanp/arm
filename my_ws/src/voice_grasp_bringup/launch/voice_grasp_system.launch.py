from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument("command_topic", default_value="/grasp_command_text"),
        DeclareLaunchArgument("asr_model", default_value="base"),
        DeclareLaunchArgument("asr_language", default_value="zh"),
        DeclareLaunchArgument("voice_audio_file", default_value=""),
        DeclareLaunchArgument("safe_wait_for_target_frame_sec", default_value="600.0"),
        DeclareLaunchArgument("grasp_start_delay_sec", default_value="1.0"),
        DeclareLaunchArgument("target_frame_topic", default_value="/grasp_target_frame"),
        DeclareLaunchArgument("wrist_yaw_topic", default_value="/wrist_target_yaw_delta"),
    ]

    command_topic = LaunchConfiguration("command_topic")
    asr_model = LaunchConfiguration("asr_model")
    asr_language = LaunchConfiguration("asr_language")
    voice_audio_file = LaunchConfiguration("voice_audio_file")
    safe_wait_for_target_frame_sec = LaunchConfiguration("safe_wait_for_target_frame_sec")
    grasp_start_delay_sec = LaunchConfiguration("grasp_start_delay_sec")
    target_frame_topic = LaunchConfiguration("target_frame_topic")
    wrist_yaw_topic = LaunchConfiguration("wrist_yaw_topic")

    safe_grasp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare("ur_bringup"), "/launch", "/start_grasp.launch.py"]
        ),
        launch_arguments={
            "grasp_command_topic": command_topic,
            "grasp_all_if_no_target": "false",
            "wait_for_target_frame_sec": safe_wait_for_target_frame_sec,
            "grasp_start_delay_sec": grasp_start_delay_sec,
            "target_frame_topic": target_frame_topic,
            "wrist_yaw_topic": wrist_yaw_topic,
        }.items(),
    )

    voice_bridge = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare("voice_grasp_bridge"), "/launch", "/voice_grasp_command.launch.py"]
        ),
        launch_arguments={
            "command_topic": command_topic,
            "audio_file": voice_audio_file,
            "asr_model": asr_model,
            "asr_language": asr_language,
        }.items(),
    )

    return LaunchDescription(declared_arguments + [safe_grasp, voice_bridge])
