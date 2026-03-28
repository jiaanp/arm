#pragma once

#include <memory>
#include <mutex>
#include <string>
#include <vector>

#include <control_msgs/action/gripper_command.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <moveit/move_group_interface/move_group_interface.h>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <std_msgs/msg/float64.hpp>
#include <std_srvs/srv/empty.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>

using GripperCommand = control_msgs::action::GripperCommand;
using GoalHandleGripperCommand = rclcpp_action::ClientGoalHandle<GripperCommand>;

class UR5ePickPlace : public rclcpp::Node {
public:
  explicit UR5ePickPlace(const rclcpp::NodeOptions &options);
  void init();
  bool plan_and_execute(const std::vector<double> &target_pose);
  bool grasp(double gripper_position);
  bool clear_octomap(double timeout_sec = 1.0);
  void get_cube_pose(const std::string &from_frame, const std::string &to_frame,
                     std::vector<double> &cube_pose);
  bool get_latest_wrist_yaw(double &yaw_value, double max_age_sec);
  void go_to_ready_position();

private:
  void goal_response_callback(const GoalHandleGripperCommand::SharedPtr &goal_handle);
  void feedback_callback(GoalHandleGripperCommand::SharedPtr,
                         const std::shared_ptr<const GripperCommand::Feedback> feedback);
  void result_callback(const GoalHandleGripperCommand::WrappedResult &result);
  void wrist_yaw_callback(const std_msgs::msg::Float64::SharedPtr msg);

  std::shared_ptr<moveit::planning_interface::MoveGroupInterface> move_group_;
  rclcpp_action::Client<GripperCommand>::SharedPtr gripper_action_client_;
  rclcpp::Client<std_srvs::srv::Empty>::SharedPtr clear_octomap_client_;
  rclcpp_action::Client<GripperCommand>::SendGoalOptions send_goal_options_;
  std::unique_ptr<tf2_ros::Buffer> tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
  rclcpp::Subscription<std_msgs::msg::Float64>::SharedPtr wrist_yaw_sub_;
  std::mutex wrist_yaw_mutex_;
  double latest_wrist_yaw_{0.0};
  rclcpp::Time latest_wrist_yaw_stamp_;
  bool has_latest_wrist_yaw_{false};
  std::string gripper_action_name_ = "/gripper_controller/gripper_cmd";
  const std::string planning_group_ = "ur_manipulator";
};
