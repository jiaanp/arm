from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument('command_topic', default_value='/voice_grasp_request'),
        DeclareLaunchArgument('raw_text_topic', default_value='/voice_pick_raw_text'),
        DeclareLaunchArgument('normalized_text_topic', default_value='/voice_pick_llm_normalized_text'),
        DeclareLaunchArgument('audio_file', default_value=''),
        DeclareLaunchArgument('sample_rate', default_value='16000'),
        DeclareLaunchArgument('channels', default_value='1'),
        DeclareLaunchArgument('chunk', default_value='1024'),
        DeclareLaunchArgument('asr_model', default_value='base'),
        DeclareLaunchArgument('asr_language', default_value='zh'),
        DeclareLaunchArgument('llm_api_key_env', default_value='DEEPSEEK_API_KEY'),
        DeclareLaunchArgument('llm_api_base', default_value='https://api.deepseek.com'),
        DeclareLaunchArgument('llm_model', default_value='deepseek-chat'),
        DeclareLaunchArgument('llm_timeout_sec', default_value='15.0'),
        DeclareLaunchArgument('publish_rule_fallback', default_value='true'),
    ]

    node = Node(
        package='voice_pick_bridge',
        executable='voice_pick_llm_command',
        name='voice_pick_llm_command',
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
                'llm_api_key_env': LaunchConfiguration('llm_api_key_env'),
                'llm_api_base': LaunchConfiguration('llm_api_base'),
                'llm_model': LaunchConfiguration('llm_model'),
                'llm_timeout_sec': LaunchConfiguration('llm_timeout_sec'),
                'publish_rule_fallback': LaunchConfiguration('publish_rule_fallback'),
            }
        ],
    )

    return LaunchDescription(declared_arguments + [node])
