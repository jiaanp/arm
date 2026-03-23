from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument("command_topic", default_value="/grasp_command_text"),
        DeclareLaunchArgument("audio_file", default_value=""),
        DeclareLaunchArgument("sample_rate", default_value="16000"),
        DeclareLaunchArgument("channels", default_value="1"),
        DeclareLaunchArgument("chunk", default_value="1024"),
        DeclareLaunchArgument("asr_model", default_value="base"),
        DeclareLaunchArgument("asr_language", default_value="zh"),
        DeclareLaunchArgument("force_simplified", default_value="true"),
        DeclareLaunchArgument("publish_empty", default_value="false"),
    ]

    node = Node(
        package="voice_grasp_bridge",
        executable="voice_grasp_command",
        name="voice_grasp_command",
        output="screen",
        parameters=[
            {
                "command_topic": LaunchConfiguration("command_topic"),
                "audio_file": LaunchConfiguration("audio_file"),
                "sample_rate": LaunchConfiguration("sample_rate"),
                "channels": LaunchConfiguration("channels"),
                "chunk": LaunchConfiguration("chunk"),
                "asr_model": LaunchConfiguration("asr_model"),
                "asr_language": LaunchConfiguration("asr_language"),
                "force_simplified": LaunchConfiguration("force_simplified"),
                "publish_empty": LaunchConfiguration("publish_empty"),
            }
        ],
    )

    return LaunchDescription(declared_arguments + [node])
