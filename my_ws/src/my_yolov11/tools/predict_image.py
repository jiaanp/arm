#!/usr/bin/env python3
import argparse
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Run YOLO prediction on an image or folder.")
    parser.add_argument("--weights", required=True, help="Path to trained .pt file.")
    parser.add_argument("--source", required=True, help="Image path, folder, or video path.")
    parser.add_argument("--project", default="runs/predict", help="Prediction output dir.")
    parser.add_argument("--name", default="predict", help="Prediction run name.")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold.")
    parser.add_argument("--device", default="", help="CUDA device id or cpu.")
    parser.add_argument("--source-root", default=".", help="Root of the my_yolov11 workspace.")
    return parser.parse_args()


def resolve_path(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (root / path).resolve()


def main():
    args = parse_args()

    try:
        from ultralytics import YOLO
    except ModuleNotFoundError as exc:
        raise SystemExit("ultralytics is not installed. Run: pip install ultralytics") from exc

    root = Path(args.source_root).expanduser().resolve()
    weights = resolve_path(root, args.weights)
    source = resolve_path(root, args.source)
    project = resolve_path(root, args.project)
    project.mkdir(parents=True, exist_ok=True)

    if not weights.exists():
        raise SystemExit(f"Weight file not found: {weights}")
    if not source.exists():
        raise SystemExit(f"Prediction source not found: {source}")

    model = YOLO(str(weights))
    results = model.predict(
        source=str(source),
        project=str(project),
        name=args.name,
        conf=args.conf,
        device=args.device,
        save=True,
    )

    save_dir = getattr(results[0], "save_dir", None) if results else None
    if save_dir:
        print(f"[predict] outputs={save_dir}")


if __name__ == "__main__":
    main()
