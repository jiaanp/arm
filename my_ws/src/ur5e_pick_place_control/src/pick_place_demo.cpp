#include "ur5e_pick_place_control/ur5e_pick_place.h"

#include <chrono>
#include <cmath>
#include <mutex>
#include <sstream>
#include <std_msgs/msg/string.hpp>
#include <string>
#include <thread>
#include <vector>

namespace {

template <typename T>
T get_or_declare_param(const std::shared_ptr<UR5ePickPlace> &node,
                       const std::string &name, const T &default_value) {
  if (!node->has_parameter(name)) {
    node->declare_parameter<T>(name, default_value);
  }
  return node->get_parameter(name).get_value<T>();
}

double wrap_to_pi(double angle) { return std::atan2(std::sin(angle), std::cos(angle)); }

std::string trim_copy(const std::string &value) {
  const auto begin = value.find_first_not_of(" \t\r\n");
  if (begin == std::string::npos) {
    return "";
  }
  const auto end = value.find_last_not_of(" \t\r\n");
  return value.substr(begin, end - begin + 1);
}

std::vector<double> parse_pose_string(const std::string &pose_str) {
  std::vector<double> pose;
  std::stringstream ss(pose_str);
  std::string token;
  while (std::getline(ss, token, ',')) {
    pose.push_back(std::stod(token));
  }
  return pose;
}

}  // namespace

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  rclcpp::NodeOptions node_options;
  node_options.automatically_declare_parameters_from_overrides(true);
  auto node = std::make_shared<UR5ePickPlace>(node_options);
  node->init();

  const double grasp_x_offset = get_or_declare_param<double>(node, "grasp_x_offset", -0.012);
  const double grasp_y_offset = get_or_declare_param<double>(node, "grasp_y_offset", 0.010);
  const double grasp_z_offset = get_or_declare_param<double>(node, "grasp_z_offset", 0.140);
  const double pre_grasp_hover_distance =
      get_or_declare_param<double>(node, "pre_grasp_hover_distance", 0.080);
  const double pre_grasp_pause_sec =
      get_or_declare_param<double>(node, "pre_grasp_pause_sec", 0.300);
  const double grasp_close_position =
      get_or_declare_param<double>(node, "grasp_close_position", 0.36);
  const double grasp_settle_time_sec =
      get_or_declare_param<double>(node, "grasp_settle_time_sec", 1.50);
  const double post_grasp_lift_height =
      get_or_declare_param<double>(node, "post_grasp_lift_height", 0.10);
  const double place_hover_distance =
      get_or_declare_param<double>(node, "place_hover_distance", 0.08);
  const double place_pause_sec = get_or_declare_param<double>(node, "place_pause_sec", 0.30);
  const bool enable_wrist_yaw_refine =
      get_or_declare_param<bool>(node, "enable_wrist_yaw_refine", true);
  const bool wrist_yaw_is_delta =
      get_or_declare_param<bool>(node, "wrist_yaw_is_delta", true);
  const double wrist_yaw_settle_time_sec =
      get_or_declare_param<double>(node, "wrist_yaw_settle_time_sec", 0.25);
  const double wrist_yaw_max_age_sec =
      get_or_declare_param<double>(node, "wrist_yaw_max_age_sec", 0.60);
  const double wrist_yaw_min_change_rad =
      get_or_declare_param<double>(node, "wrist_yaw_min_change_rad", 0.01);
  std::string target_cube_frame =
      trim_copy(get_or_declare_param<std::string>(node, "target_cube_frame", ""));
  const std::string target_frame_topic =
      get_or_declare_param<std::string>(node, "target_frame_topic", "/grasp_target_frame");
  const double wait_for_target_frame_sec =
      get_or_declare_param<double>(node, "wait_for_target_frame_sec", 3.0);
  const std::string place_zone =
      trim_copy(get_or_declare_param<std::string>(node, "place_zone", "middle"));
  const std::string left_zone_pose_str =
      get_or_declare_param<std::string>(node, "left_zone_pose", "0.38, -0.36, 0.22, 0.0, 3.14, 0.0");
  const std::string middle_zone_pose_str =
      get_or_declare_param<std::string>(node, "middle_zone_pose", "0.38, 0.00, 0.22, 0.0, 3.14, 0.0");
  const std::string right_zone_pose_str =
      get_or_declare_param<std::string>(node, "right_zone_pose", "0.38, 0.36, 0.22, 0.0, 3.14, 0.0");

  std::vector<double> place_pose;
  if (place_zone == "left") {
    place_pose = parse_pose_string(left_zone_pose_str);
  } else if (place_zone == "right") {
    place_pose = parse_pose_string(right_zone_pose_str);
  } else {
    place_pose = parse_pose_string(middle_zone_pose_str);
  }

  std::mutex target_frame_mutex;
  std::string topic_target_cube_frame;
  bool has_topic_target_frame = false;
  auto target_frame_sub = node->create_subscription<std_msgs::msg::String>(
      target_frame_topic, 10,
      [&](const std_msgs::msg::String::SharedPtr msg) {
        const auto value = trim_copy(msg->data);
        if (value.empty()) {
          return;
        }
        std::lock_guard<std::mutex> lock(target_frame_mutex);
        topic_target_cube_frame = value;
        has_topic_target_frame = true;
      });
  (void)target_frame_sub;

  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(node);
  std::thread([&executor]() { executor.spin(); }).detach();

  if (target_cube_frame.empty() && wait_for_target_frame_sec > 0.0) {
    const auto wait_start = node->get_clock()->now();
    while (rclcpp::ok()) {
      {
        std::lock_guard<std::mutex> lock(target_frame_mutex);
        if (has_topic_target_frame) {
          target_cube_frame = topic_target_cube_frame;
          break;
        }
      }
      const auto wait_elapsed = (node->get_clock()->now() - wait_start).seconds();
      if (wait_elapsed >= wait_for_target_frame_sec) {
        break;
      }
      rclcpp::sleep_for(std::chrono::milliseconds(50));
    }
  }

  if (target_cube_frame.empty()) {
    RCLCPP_WARN(node->get_logger(), "No selected target frame, exiting.");
    rclcpp::shutdown();
    return 0;
  }

  RCLCPP_INFO(node->get_logger(), "Using selected target frame: %s", target_cube_frame.c_str());

  std::vector<double> cube_pose;
  node->get_cube_pose("base_link", target_cube_frame, cube_pose);
  if (cube_pose.empty()) {
    RCLCPP_WARN(node->get_logger(), "Failed to get pose for %s", target_cube_frame.c_str());
    rclcpp::shutdown();
    return 0;
  }

  cube_pose[0] += grasp_x_offset;
  cube_pose[1] += grasp_y_offset;
  cube_pose[2] += grasp_z_offset;
  cube_pose[3] = 0.0;
  cube_pose[4] = M_PI;
  cube_pose[5] = 0.0;

  std::vector<double> grasp_pose = cube_pose;
  std::vector<double> pre_grasp_pose = grasp_pose;
  std::vector<double> post_grasp_pose = grasp_pose;
  pre_grasp_pose[2] += pre_grasp_hover_distance;
  post_grasp_pose[2] += post_grasp_lift_height;

  if (enable_wrist_yaw_refine) {
    double yaw_value = 0.0;
    if (node->get_latest_wrist_yaw(yaw_value, wrist_yaw_max_age_sec)) {
      const double yaw_target =
          wrist_yaw_is_delta ? wrap_to_pi(pre_grasp_pose[5] + yaw_value) : wrap_to_pi(yaw_value);
      const double yaw_delta = wrap_to_pi(yaw_target - pre_grasp_pose[5]);
      if (std::fabs(yaw_delta) >= wrist_yaw_min_change_rad) {
        pre_grasp_pose[5] = yaw_target;
        grasp_pose[5] = yaw_target;
        if (wrist_yaw_settle_time_sec > 0.0) {
          rclcpp::sleep_for(std::chrono::duration_cast<std::chrono::nanoseconds>(
              std::chrono::duration<double>(wrist_yaw_settle_time_sec)));
        }
      }
    }
  }

  node->go_to_ready_position();
  node->grasp(0.0);
  rclcpp::sleep_for(std::chrono::seconds(1));

  if (!node->plan_and_execute(pre_grasp_pose)) {
    RCLCPP_WARN(node->get_logger(), "Pre-grasp hover move failed");
    rclcpp::shutdown();
    return 0;
  }
  if (pre_grasp_pause_sec > 0.0) {
    rclcpp::sleep_for(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::duration<double>(pre_grasp_pause_sec)));
  }
  if (!node->plan_and_execute(grasp_pose)) {
    RCLCPP_WARN(node->get_logger(), "Descend to grasp pose failed");
    rclcpp::shutdown();
    return 0;
  }
  node->grasp(grasp_close_position);
  if (grasp_settle_time_sec > 0.0) {
    rclcpp::sleep_for(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::duration<double>(grasp_settle_time_sec)));
  }
  if (!node->plan_and_execute(post_grasp_pose)) {
    RCLCPP_WARN(node->get_logger(), "Post-grasp lift failed");
    rclcpp::shutdown();
    return 0;
  }

  std::vector<double> place_hover_pose = place_pose;
  place_hover_pose[2] += place_hover_distance;
  if (!node->plan_and_execute(place_hover_pose)) {
    RCLCPP_WARN(node->get_logger(), "Move to place hover failed");
    rclcpp::shutdown();
    return 0;
  }
  if (!node->plan_and_execute(place_pose)) {
    RCLCPP_WARN(node->get_logger(), "Move to place pose failed");
    rclcpp::shutdown();
    return 0;
  }
  if (place_pause_sec > 0.0) {
    rclcpp::sleep_for(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::duration<double>(place_pause_sec)));
  }
  node->grasp(0.0);
  rclcpp::sleep_for(std::chrono::seconds(1));
  if (!node->plan_and_execute(place_hover_pose)) {
    RCLCPP_WARN(node->get_logger(), "Retreat after place failed");
  }
  node->go_to_ready_position();

  rclcpp::shutdown();
  return 0;
}
