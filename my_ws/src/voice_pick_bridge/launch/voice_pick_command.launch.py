from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument('command_topic', default_value='/voice_grasp_request'),
        DeclareLaunchArgument('raw_text_topic', default_value='/voice_pick_raw_text'),
        DeclareLaunchArgument('normalized_text_topic', default_value='/voice_pick_normalized_text'),
        DeclareLaunchArgument('audio_file', default_value=''),
        DeclareLaunchArgument('sample_rate', default_value='16000'),
        DeclareLaunchArgument('channels', default_value='1'),
        DeclareLaunchArgument('chunk', default_value='1024'),
        DeclareLaunchArgument('asr_model', default_value='base'),
        DeclareLaunchArgument('asr_language', default_value='zh'),
    ]

    node = Node(
        package='voice_pick_bridge',
        executable='voice_pick_command',
        name='voice_pick_command',
        output='screen',
        parameters=[
            {
                'command_topic': LaunchConfiguration('command_topic'),
                'raw_text_topic': LaunchConfiguration('raw_text_topic'),
                'normalized_text_topic': LaunchConfiguration('normalized_text_topic'),
                'audio_file': LaunchConfiguration('audio_file'),
                'sample_rate': LaunchConfiguration('sample_rate'),
                'channels': LaunchConfiguration('channels'),
                'chunk': LaunchConfiguration('chunk'),
                'asr_model': LaunchConfiguration('asr_model'),
                'asr_language': LaunchConfiguration('asr_language'),
            }
        ],
    )

    return LaunchDescription(declared_arguments + [node])
