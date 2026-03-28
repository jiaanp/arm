# my_yolov11

Minimal training workspace for a custom YOLO11 detection model that can
replace the current cube detector in the ROS project.

## Goal

Train your own detection model and export a `best.pt` that can be tested
locally first, then copied into:

`/home/hw/arm-1/my_ws/src/vision/vision/yolov11/models/best.pt`

The current ROS pipeline works best if your dataset uses a single class named
`cube`.

## Folder Layout

```text
my_yolov11/
  configs/
    cube_detect.yaml
  dataset/
    images/
      train/
      val/
    labels/
      train/
      val/
  raw/
    images/
    labels/
  runs/
  tools/
    train.py
    split_dataset.py
    predict_image.py
    copy_best_to_vision.py
```

## Recommended Workflow

1. Collect images.
2. Annotate them in YOLO detection format.
3. Put raw images into `raw/images/` and raw label files into `raw/labels/`.
4. Run the split script.
5. Run training.
6. Test the trained weight on an image.
7. Copy the trained `best.pt` into the ROS detector path.

## 1. Collect Images

You can reuse the existing ROS recorder:

`/home/hw/arm-1/my_ws/src/vision/vision/record.py`

Or collect images by any other method. More data diversity is better:

- different cube positions
- different distances
- partial occlusion
- different lighting
- 1 to 6 cubes in the same frame

## 2. Annotate

Use any annotation tool that exports YOLO detection labels.

Recommended:

- Label Studio
- LabelImg
- CVAT
- Roboflow

Each image should have one `.txt` label file with lines like:

```text
0 0.512500 0.458333 0.101562 0.145833
```

If you want the ROS side to keep working without code changes, keep:

- class count: `1`
- class name: `cube`

## 3. Split Raw Data

Place all annotated pairs here first:

- `raw/images/`
- `raw/labels/`

Then run:

```bash
python3 tools/split_dataset.py --source-root . --val-ratio 0.2
```

This will copy matched image/label pairs into:

- `dataset/images/train`
- `dataset/images/val`
- `dataset/labels/train`
- `dataset/labels/val`

## 4. Train

Install dependencies in your training environment first.

Minimal requirement:

```bash
pip install ultralytics
```

Then train:

```bash
python3 tools/train.py \
  --source-root . \
  --data configs/cube_detect.yaml \
  --model yolo11n.pt \
  --imgsz 640 \
  --epochs 100 \
  --batch 16
```

Useful notes:

- `yolo11n.pt` is a good starting point for fast iteration.
- `yolo11s.pt` may improve accuracy if your GPU allows it.
- If your GPU memory is tight, reduce `--batch`.

## 5. Predict on a Sample Image

```bash
python3 tools/predict_image.py \
  --weights runs/detect/cube_detect/weights/best.pt \
  --source path/to/test.jpg
```

By default the script saves outputs under `runs/predict/`.

## 6. Copy the Best Weight into the ROS Project

```bash
python3 tools/copy_best_to_vision.py \
  --weights runs/detect/cube_detect/weights/best.pt
```

This creates a backup of the old detector weight before replacing it.

## Suggested First Experiment

- single class: `cube`
- detector task only
- `imgsz=640`
- `epochs=100`
- `batch=16`

Get a stable detector first. Keep color reasoning and 3D localization in the
existing ROS pipeline.

## Extra Tools

### Record images directly from ROS

```bash
python3 tools/record_ros_images.py \
  --output-dir /home/hw/arm-1/my_ws/src/my_yolov11/raw/images \
  --image-topic /color/image_raw \
  --interval-sec 3.0 \
  --init-index 0
```

### Validate labels before splitting and training

```bash
python3 tools/validate_dataset.py --source-root .
```

This checks:

- image and label pairing
- YOLO label field count
- class id range
- normalized box values in `[0, 1]`
