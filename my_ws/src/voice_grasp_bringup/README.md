# voice_grasp_bringup

独立的语音抓取 wrapper 包，不修改现有工程文件。

当前包提供的入口：
- `voice_grasp_system.launch.py`

它会组合启动：
- 语音桥接节点
- 安全参数包装后的 `start_grasp.launch.py`

## 适用场景

这个包适合你想快速把“语音输入 + 原始抓取链路”连起来时使用。

如果你现在使用的是更新后的三终端常驻会话流程，更推荐：
- 仿真：`ros2 launch ur_bringup simulation.launch.py`
- 抓取会话：`ros2 launch ur_bringup voice_triggered_grasp.launch.py`
- 语音节点：`ros2 run voice_pick_bridge voice_pick_command`

## 构建

```bash
cd /home/hw/arm-1/my_ws
colcon build --packages-select voice_grasp_bridge voice_grasp_bringup
source install/setup.bash
```

## 运行

```bash
ros2 launch voice_grasp_bringup voice_grasp_system.launch.py
```

## 安全策略

仍然复用现有：
- [`ur_bringup/launch/start_grasp.launch.py`](/home/hw/arm-1/my_ws/src/ur_bringup/launch/start_grasp.launch.py)

不会修改该文件，而是在外层传安全参数：
- `grasp_all_if_no_target:=false`
- `wait_for_target_frame_sec:=600.0`

这样抓取节点会等待视觉解析后的目标，而不是在无目标时直接抓全部方块。
