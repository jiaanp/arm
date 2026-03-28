#include "ur5e_pick_place_control/ur5e_pick_place.h"

#include <chrono>
#include <future>

UR5ePickPlace::UR5ePickPlace(const rclcpp::NodeOptions &options)
    : Node("ur5e_pick_place", options), latest_wrist_yaw_stamp_(this->get_clock()->now()) {
  gripper_action_client_ = rclcpp_action::create_client<GripperCommand>(this, gripper_action_name_);
  clear_octomap_client_ = this->create_client<std_srvs::srv::Empty>("/clear_octomap");
  send_goal_options_.goal_response_callback =
      std::bind(&UR5ePickPlace::goal_response_callback, this, std::placeholders::_1);
  send_goal_options_.feedback_callback =
      std::bind(&UR5ePickPlace::feedback_callback, this, std::placeholders::_1, std::placeholders::_2);
  send_goal_options_.result_callback =
      std::bind(&UR5ePickPlace::result_callback, this, std::placeholders::_1);

  tf_buffer_ = std::make_unique<tf2_ros::Buffer>(this->get_clock());
  tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);
  RCLCPP_INFO(this->get_logger(), "Create Tf buffer and listener");

  if (!this->has_parameter("wrist_yaw_topic")) {
    this->declare_parameter<std::string>("wrist_yaw_topic", "/wrist_target_yaw_delta");
  }
  const auto wrist_yaw_topic = this->get_parameter("wrist_yaw_topic").as_string();
  wrist_yaw_sub_ = this->create_subscription<std_msgs::msg::Float64>(
      wrist_yaw_topic, 10,
      std::bind(&UR5ePickPlace::wrist_yaw_callback, this, std::placeholders::_1));
  RCLCPP_INFO(this->get_logger(), "Listening wrist yaw topic: %s", wrist_yaw_topic.c_str());
}

void UR5ePickPlace::init() {
  move_group_ = std::make_shared<moveit::planning_interface::MoveGroupInterface>(
      shared_from_this(), planning_group_);
  move_group_->allowReplanning(true);
  move_group_->setPlanningTime(5.0);
}

void UR5ePickPlace::goal_response_callback(const GoalHandleGripperCommand::SharedPtr &goal_handle) {
  if (!goal_handle) {
    RCLCPP_ERROR(this->get_logger(), "Goal was rejected by server");
  } else {
    RCLCPP_INFO(this->get_logger(), "Goal accepted by server, waiting for result");
  }
}

void UR5ePickPlace::feedback_callback(
    GoalHandleGripperCommand::SharedPtr,
    const std::shared_ptr<const GripperCommand::Feedback> feedback) {
  RCLCPP_INFO(this->get_logger(), "Got Feedback: Current position is %f", feedback->position);
}

void UR5ePickPlace::result_callback(const GoalHandleGripperCommand::WrappedResult &result) {
  switch (result.code) {
    case rclcpp_action::ResultCode::SUCCEEDED:
      break;
    case rclcpp_action::ResultCode::ABORTED:
      RCLCPP_ERROR(this->get_logger(), "Goal was aborted");
      return;
    case rclcpp_action::ResultCode::CANCELED:
      RCLCPP_ERROR(this->get_logger(), "Goal was canceled");
      return;
    default:
      RCLCPP_ERROR(this->get_logger(), "Unknown result code");
      return;
  }
  RCLCPP_INFO(this->get_logger(), "Goal is completed, current position is %f",
              result.result->position);
}

bool UR5ePickPlace::grasp(double gripper_position) {
  if (!gripper_action_client_->wait_for_action_server(std::chrono::seconds(10))) {
    RCLCPP_ERROR(this->get_logger(), "Action server not available after waiting");
    return false;
  }
  auto gripper_goal_msg = GripperCommand::Goal();
  gripper_goal_msg.command.position = gripper_position;
  gripper_goal_msg.command.max_effort = -1.0;
  RCLCPP_INFO(this->get_logger(), "Sending gripper goal");
  gripper_action_client_->async_send_goal(gripper_goal_msg, send_goal_options_);
  return true;
}

bool UR5ePickPlace::clear_octomap(double timeout_sec) {
  if (!clear_octomap_client_) {
    RCLCPP_WARN(this->get_logger(), "clear_octomap client is not initialized");
    return false;
  }

  const auto timeout = std::chrono::duration_cast<std::chrono::nanoseconds>(
      std::chrono::duration<double>(timeout_sec));
  if (!clear_octomap_client_->wait_for_service(timeout)) {
    RCLCPP_WARN(this->get_logger(),
                "clear_octomap service not available within %.2f s", timeout_sec);
    return false;
  }

  auto request = std::make_shared<std_srvs::srv::Empty::Request>();
  auto future = clear_octomap_client_->async_send_request(request);
  if (future.wait_for(timeout) != std::future_status::ready) {
    RCLCPP_WARN(this->get_logger(), "Failed to call clear_octomap service");
    return false;
  }

  try {
    future.get();
  } catch (const std::exception &ex) {
    RCLCPP_WARN(this->get_logger(), "clear_octomap service call failed: %s", ex.what());
    return false;
  }

  RCLCPP_INFO(this->get_logger(), "Cleared octomap before final approach");
  return true;
}

bool UR5ePickPlace::plan_and_execute(const std::vector<double> &target_pose) {
  if (target_pose.size() != 6) {
    return false;
  }
  geometry_msgs::msg::PoseStamped target_pose_stamped;
  target_pose_stamped.header.frame_id = "base_link";
  target_pose_stamped.pose.position.x = target_pose[0];
  target_pose_stamped.pose.position.y = target_pose[1];
  target_pose_stamped.pose.position.z = target_pose[2];
  tf2::Quaternion quat;
  quat.setRPY(target_pose[3], target_pose[4], target_pose[5]);
  quat.normalize();
  target_pose_stamped.pose.orientation.x = quat.x();
  target_pose_stamped.pose.orientation.y = quat.y();
  target_pose_stamped.pose.orientation.z = quat.z();
  target_pose_stamped.pose.orientation.w = quat.w();

  std::vector<double> joint_target_positions = move_group_->getCurrentJointValues();
  move_group_->setJointValueTarget(target_pose_stamped);
  move_group_->getJointValueTarget(joint_target_positions);
  move_group_->setJointValueTarget(joint_target_positions);
  moveit::planning_interface::MoveGroupInterface::Plan plan;
  bool success_plan = (move_group_->plan(plan) == moveit::core::MoveItErrorCode::SUCCESS);
  if (success_plan) {
    move_group_->execute(plan);
    return true;
  }
  RCLCPP_ERROR(this->get_logger(), "Failed to plan");
  return false;
}

void UR5ePickPlace::get_cube_pose(const std::string &from_frame, const std::string &to_frame,
                                  std::vector<double> &cube_pose) {
  geometry_msgs::msg::TransformStamped tf_msg;
  cube_pose.clear();
  try {
    tf_msg = tf_buffer_->lookupTransform(from_frame, to_frame, tf2::TimePointZero);
  } catch (tf2::TransformException &ex) {
    RCLCPP_WARN(this->get_logger(), "Failed to get transform %s -> %s: %s",
                from_frame.c_str(), to_frame.c_str(), ex.what());
    return;
  }
  cube_pose = {tf_msg.transform.translation.x, tf_msg.transform.translation.y,
               tf_msg.transform.translation.z, 0.0, 0.0, 0.0};
}

bool UR5ePickPlace::get_latest_wrist_yaw(double &yaw_value, double max_age_sec) {
  std::lock_guard<std::mutex> lock(wrist_yaw_mutex_);
  if (!has_latest_wrist_yaw_) {
    return false;
  }
  const auto age = (this->get_clock()->now() - latest_wrist_yaw_stamp_).seconds();
  if (age < 0.0 || age > max_age_sec) {
    return false;
  }
  yaw_value = latest_wrist_yaw_;
  return true;
}

void UR5ePickPlace::go_to_ready_position() {
  move_group_->setNamedTarget("ready");
  move_group_->move();
}

void UR5ePickPlace::wrist_yaw_callback(const std_msgs::msg::Float64::SharedPtr msg) {
  std::lock_guard<std::mutex> lock(wrist_yaw_mutex_);
  latest_wrist_yaw_ = msg->data;
  latest_wrist_yaw_stamp_ = this->get_clock()->now();
  has_latest_wrist_yaw_ = true;
}
