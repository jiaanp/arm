import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    robot_description_kinematics = PathJoinSubstitution(
        [FindPackageShare('ur5e_gripper_moveit_config'), 'config', 'kinematics.yaml']
    )
    place_pose_config = os.path.join(
        get_package_share_directory('ur5e_pick_place_control'), 'config', 'place_zone_poses.yaml'
    )

    declared_arguments = [
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
        DeclareLaunchArgument('place_zone', default_value='middle'),
        DeclareLaunchArgument('enable_wrist_yaw_refine', default_value='true'),
        DeclareLaunchArgument('wrist_yaw_topic', default_value='/wrist_target_yaw_delta'),
        DeclareLaunchArgument('wrist_yaw_is_delta', default_value='true'),
        DeclareLaunchArgument('wrist_yaw_settle_time_sec', default_value='0.25'),
        DeclareLaunchArgument('wrist_yaw_max_age_sec', default_value='0.60'),
        DeclareLaunchArgument('wrist_yaw_min_change_rad', default_value='0.01'),
        DeclareLaunchArgument('target_cube_frame', default_value=''),
        DeclareLaunchArgument('target_frame_topic', default_value='/grasp_target_frame'),
        DeclareLaunchArgument('wait_for_target_frame_sec', default_value='3.0'),
    ]

    node = Node(
        package='ur5e_pick_place_control',
        executable='pick_place_demo',
        name='pick_place_demo_node',
        parameters=[
            {
                'use_sim_time': True,
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
                'place_zone': LaunchConfiguration('place_zone'),
                'enable_wrist_yaw_refine': LaunchConfiguration('enable_wrist_yaw_refine'),
                'wrist_yaw_topic': LaunchConfiguration('wrist_yaw_topic'),
                'wrist_yaw_is_delta': LaunchConfiguration('wrist_yaw_is_delta'),
                'wrist_yaw_settle_time_sec': LaunchConfiguration('wrist_yaw_settle_time_sec'),
                'wrist_yaw_max_age_sec': LaunchConfiguration('wrist_yaw_max_age_sec'),
                'wrist_yaw_min_change_rad': LaunchConfiguration('wrist_yaw_min_change_rad'),
                'target_cube_frame': LaunchConfiguration('target_cube_frame'),
                'target_frame_topic': LaunchConfiguration('target_frame_topic'),
                'wait_for_target_frame_sec': LaunchConfiguration('wait_for_target_frame_sec'),
            },
            robot_description_kinematics,
            place_pose_config,
        ],
        output='screen',
    )

    return LaunchDescription(declared_arguments + [node])
