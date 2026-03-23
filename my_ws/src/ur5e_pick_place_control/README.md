# ur5e_pick_place_control

独立的固定区域 pick-place 执行包。

这个包不会去改原始的 `ur5e_gripper_control` 抓取文件，而是新建一套执行链，用于：
- 等待视觉选出的目标方块 frame
- 执行抓取
- 放到固定区域
- 回到安全位置

## 功能

支持三个固定放置区：
- `left`
- `middle`
- `right`

放置位姿配置文件：
[`config/place_zone_poses.yaml`](/home/hw/arm-1/my_ws/src/ur5e_pick_place_control/config/place_zone_poses.yaml)

主要 launch：
- [`pick_place_demo.launch.py`](/home/hw/arm-1/my_ws/src/ur5e_pick_place_control/launch/pick_place_demo.launch.py)
- [`start_pick_place.launch.py`](/home/hw/arm-1/my_ws/src/ur5e_pick_place_control/launch/start_pick_place.launch.py)

## 构建

```bash
cd /home/hw/arm-1/my_ws
colcon build --packages-select ur5e_pick_place_control
source install/setup.bash
```

## 运行方式

直接启动执行链：

```bash
ros2 launch ur5e_pick_place_control pick_place_demo.launch.py place_zone:=middle
```

像原始抓取 launch 一样，带命令自动发布：

```bash
ros2 launch ur5e_pick_place_control start_pick_place.launch.py \
  grasp_command_text:='抓红色方块' \
  place_zone:=left
```

## 关键参数

- `place_zone`: `left` / `middle` / `right`
- `target_frame_topic`: 默认 `/grasp_target_frame`
- `wait_for_target_frame_sec`: 等待视觉目标的超时时间
- `wrist_yaw_topic`: 默认 `/wrist_target_yaw_delta`
- `grasp_x_offset` / `grasp_y_offset` / `grasp_z_offset`: 抓取偏移

## 说明

这个包依赖：
- Gazebo / MoveIt 仿真链路已经启动
- 视觉侧能够根据 `/grasp_command_text` 正确发布 `/grasp_target_frame`

如果抓取命令已发布但日志提示没有目标 frame，优先检查：
- 视觉检测是否正常
- `/grasp_command_text` 是否收到命令
- `/grasp_target_frame` 是否在等待时间内发布
