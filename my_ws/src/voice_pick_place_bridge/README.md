# voice_pick_place_bridge

固定区域放置版本的语音桥接包。

主要节点：
- `voice_pick_place_command`: 录音、ASR、解析“抓取 + 放置区域”请求
- `pick_place_session`: 常驻会话，按请求依次触发 pick-place 执行

默认 request topic：
- `/voice_pick_place_request`

## 支持的命令

示例命令：
- `抓红色方块放到左侧区域`
- `抓最左边的方块放到中间区域`
- `抓蓝色方块放到右侧区域`

终端会打印：
- `ASR: ...`
- `REQ: {'pick_command': '...', 'place_zone': 'left|middle|right'}`

## 构建

```bash
cd /home/hw/arm-1/my_ws
colcon build --packages-select voice_pick_place_bridge ur5e_pick_place_control
source install/setup.bash
```

## 运行

推荐三终端中的后两项：

常驻会话：

```bash
ros2 run voice_pick_place_bridge pick_place_session
```

语音命令：

```bash
ros2 run voice_pick_place_bridge voice_pick_place_command
```

也提供 launch：

```bash
ros2 launch voice_pick_place_bridge pick_place_session.launch.py
```

说明：
- `pick_place_session` 常驻等待下一条命令
- `voice_pick_place_command` 是交互式录音节点，更推荐 `ros2 run`
- 放置区域解析只会在 `放到` / `放在` 后半句中进行，避免被“最左边的方块”误伤
