#include "ur5e_gripper_control/ur5e_gripper.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include <std_msgs/msg/string.hpp>

namespace {

// 如果参数尚未声明，就用默认值声明并读取。
template <typename T>
T get_or_declare_param(const std::shared_ptr<UR5eGripper> &node,
                       const std::string &name, const T &default_value) {
  if (!node->has_parameter(name)) {
    node->declare_parameter<T>(name, default_value);
  }
  return node->get_parameter(name).get_value<T>();
}

// 将角度归一化到 [-pi, pi]，避免 yaw 更新出现跳变。
double wrap_to_pi(double angle) {
  return std::atan2(std::sin(angle), std::cos(angle));
}

// 去掉输入命令字符串首尾的空白字符。
std::string trim_copy(const std::string &value) {
  const auto begin = value.find_first_not_of(" \t\r\n");
  if (begin == std::string::npos) {
    return "";
  }
  const auto end = value.find_last_not_of(" \t\r\n");
  return value.substr(begin, end - begin + 1);
}

} // namespace

int main(int argc, char **argv) {
  // 创建 ROS 节点，并初始化对 MoveIt 的封装。
  rclcpp::init(argc, argv);
  rclcpp::NodeOptions node_options;
  node_options.automatically_declare_parameters_from_overrides(true);
  auto node = std::make_shared<UR5eGripper>(node_options);
  node->init();

  // 读取抓取流程相关参数，包括接近、抓取、抬升和目标选择策略。
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
  const bool clear_octomap_on_final_approach =
      get_or_declare_param<bool>(node, "clear_octomap_on_final_approach", true);
  const double octomap_clear_timeout_sec =
      get_or_declare_param<double>(node, "octomap_clear_timeout_sec", 1.0);
  const double octomap_clear_wait_sec =
      get_or_declare_param<double>(node, "octomap_clear_wait_sec", 0.15);
  const double octomap_recovery_wait_sec =
      get_or_declare_param<double>(node, "octomap_recovery_wait_sec", 0.50);

  const bool enable_wrist_yaw_refine =
      get_or_declare_param<bool>(node, "enable_wrist_yaw_refine", true);
  const bool wrist_yaw_is_delta =
      get_or_declare_param<bool>(node, "wrist_yaw_is_delta", true);
  const double wrist_yaw_settle_time_sec =
      get_or_declare_param<double>(node, "wrist_yaw_settle_time_sec", 0.25);
  const double wrist_yaw_max_age_sec =
      get_or_declare_param<double>(node, "wrist_yaw_max_age_sec", 1.50);
  const double wrist_yaw_min_change_rad =
      get_or_declare_param<double>(node, "wrist_yaw_min_change_rad", 0.01);
  std::string target_cube_frame =
      trim_copy(get_or_declare_param<std::string>(node, "target_cube_frame", ""));
  const std::string target_frame_topic =
      get_or_declare_param<std::string>(node, "target_frame_topic", "/grasp_target_frame");
  const double wait_for_target_frame_sec =
      get_or_declare_param<double>(node, "wait_for_target_frame_sec", 3.0);
  const bool grasp_all_if_no_target =
      get_or_declare_param<bool>(node, "grasp_all_if_no_target", true);

  // 订阅视觉/命令选择链路发布的目标坐标系。
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

  // 在后台线程处理回调，让主线程可以按顺序执行抓取流程。
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(node);
  std::thread([&executor]() { executor.spin(); }).detach();

  // 读取预设放置位姿，并准备本次要处理的目标方块列表。
  std::vector<std::vector<double>> target_pose_list;
  node->get_target_pose_list(target_pose_list);
  const std::string from_frame = "base_link";
  std::vector<std::string> to_frame_list;

  // 先等待一段时间接收目标 frame，再决定是否走回退逻辑。
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

  // 优先使用已选中的目标方块；若没有目标，则按配置决定是否回退到默认方块列表。
  if (!target_cube_frame.empty()) {
    to_frame_list.push_back(target_cube_frame);
    RCLCPP_INFO(rclcpp::get_logger("demo4"), "Using selected target frame: %s",
                target_cube_frame.c_str());
  } else if (grasp_all_if_no_target) {
    to_frame_list = {"cube1", "cube2", "cube3", "cube4", "cube5", "cube6"};
    RCLCPP_WARN(rclcpp::get_logger("demo4"),
                "No selected target frame, fallback to grasp all cubes.");
  } else {
    RCLCPP_WARN(rclcpp::get_logger("demo4"),
                "No selected target frame and fallback disabled, exiting.");
    node->go_to_ready_position();
    rclcpp::shutdown();
    return 0;
  }

  // 查询每个方块的 TF 位姿，并叠加末端执行器抓取偏移，生成抓取位姿。
  std::vector<std::vector<double>> cube_pose_list;
  for (const auto &to_frame : to_frame_list) {
    std::vector<double> cube_pose;
    node->get_cube_pose(from_frame, to_frame, cube_pose);
    if (cube_pose.empty()) {
      RCLCPP_WARN(rclcpp::get_logger("demo4"), "Failed to get pose for %s, skipping",
                  to_frame.c_str());
      continue;
    }

    cube_pose[0] += grasp_x_offset;
    cube_pose[1] += grasp_y_offset;
    cube_pose[2] += grasp_z_offset;
    cube_pose[3] = 0.0;
    cube_pose[4] = M_PI;
    cube_pose[5] = 0.0;
    RCLCPP_INFO(rclcpp::get_logger("demo4"),
                "Adjusted cube pose for %s: x=%f, y=%f, z=%f", to_frame.c_str(),
                cube_pose[0], cube_pose[1], cube_pose[2]);
    cube_pose_list.push_back(cube_pose);
  }

  // 对每个有效目标依次执行完整的抓取与放置流程。
  for (size_t i = 0; i < std::min<size_t>(6, cube_pose_list.size()); i++) {
    std::vector<double> grasp_pose = cube_pose_list[i];
    std::vector<double> pre_grasp_pose = grasp_pose;
    pre_grasp_pose[2] += pre_grasp_hover_distance;

    // 先移动到目标上方的安全悬停位姿。
    if (!node->plan_and_execute(pre_grasp_pose)) {
      RCLCPP_WARN(rclcpp::get_logger("demo4"),
                  "Pre-grasp hover move failed for index %zu", i);
      continue;
    }
    if (pre_grasp_pause_sec > 0.0) {
      rclcpp::sleep_for(
          std::chrono::duration_cast<std::chrono::nanoseconds>(
              std::chrono::duration<double>(pre_grasp_pause_sec)));
    }

    // 在下探之前，可选地使用腕部相机结果修正末端 yaw。
    if (enable_wrist_yaw_refine) {
      if (wrist_yaw_settle_time_sec > 0.0) {
        rclcpp::sleep_for(
            std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::duration<double>(wrist_yaw_settle_time_sec)));
      }

      double yaw_value = 0.0;
      if (node->get_latest_wrist_yaw(yaw_value, wrist_yaw_max_age_sec)) {
        const double yaw_target =
            wrist_yaw_is_delta ? wrap_to_pi(pre_grasp_pose[5] + yaw_value)
                               : wrap_to_pi(yaw_value);
        const double yaw_delta = wrap_to_pi(yaw_target - pre_grasp_pose[5]);

        if (std::fabs(yaw_delta) >= wrist_yaw_min_change_rad) {
          pre_grasp_pose[5] = yaw_target;
          grasp_pose[5] = yaw_target;
          if (node->plan_and_execute(pre_grasp_pose)) {
            RCLCPP_INFO(rclcpp::get_logger("demo4"),
                        "Wrist yaw refined for index %zu: source=%.3f rad (%s), "
                        "target=%.3f rad, delta=%.3f rad",
                        i, yaw_value, wrist_yaw_is_delta ? "delta" : "absolute",
                        yaw_target, yaw_delta);
          } else {
            RCLCPP_WARN(rclcpp::get_logger("demo4"),
                        "Failed to execute wrist yaw refinement for index %zu", i);
          }
        } else {
          RCLCPP_INFO(rclcpp::get_logger("demo4"),
                      "Wrist yaw change too small (|%.4f| < %.4f), skip",
                      yaw_delta, wrist_yaw_min_change_rad);
        }
      } else {
        RCLCPP_WARN(rclcpp::get_logger("demo4"),
                    "No fresh wrist yaw sample (max age %.2fs), skip refinement",
                    wrist_yaw_max_age_sec);
      }
    }

    // 最后一小段靠近抓取目标前，清空 octomap，避免把目标自己当成障碍。
    if (clear_octomap_on_final_approach) {
      node->clear_octomap(octomap_clear_timeout_sec);
      if (octomap_clear_wait_sec > 0.0) {
        rclcpp::sleep_for(
            std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::duration<double>(octomap_clear_wait_sec)));
      }
    }

    // 从悬停位姿下探到最终抓取位姿。
    if (!node->plan_and_execute(grasp_pose)) {
      RCLCPP_WARN(rclcpp::get_logger("demo4"),
                  "Descend to grasp pose failed for index %zu", i);
      continue;
    }

    // 闭合夹爪，等待抓取稳定后再抬升物体。
    node->grasp(grasp_close_position);
    if (grasp_settle_time_sec > 0.0) {
      rclcpp::sleep_for(
          std::chrono::duration_cast<std::chrono::nanoseconds>(
              std::chrono::duration<double>(grasp_settle_time_sec)));
    }

    std::vector<double> post_grasp_pose = grasp_pose;
    post_grasp_pose[2] += post_grasp_lift_height;
    if (!node->plan_and_execute(post_grasp_pose)) {
      RCLCPP_WARN(rclcpp::get_logger("demo4"),
                  "Post-grasp lift failed for index %zu", i);
    }
    if (octomap_recovery_wait_sec > 0.0) {
      rclcpp::sleep_for(
          std::chrono::duration_cast<std::chrono::nanoseconds>(
              std::chrono::duration<double>(octomap_recovery_wait_sec)));
    }

    // 移动到当前槽位对应的放置位姿，并释放物体。
    if (i < target_pose_list.size()) {
      const bool place_success = node->plan_and_execute(target_pose_list[i]);
      if (place_success) {
        node->grasp(0.0);
        rclcpp::sleep_for(std::chrono::seconds(1));
      }
    }
  }

  // 结束前回到命名的 ready 姿态，再关闭节点。
  node->go_to_ready_position();
  rclcpp::shutdown();
  return 0;
}
