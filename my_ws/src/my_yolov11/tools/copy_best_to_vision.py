#!/usr/bin/env python3
import argparse
import shutil
from datetime import datetime
from pathlib import Path


DEFAULT_TARGET = "/home/hw/arm-1/my_ws/src/vision/vision/yolov11/models/best.pt"


def parse_args():
    parser = argparse.ArgumentParser(description="Copy a trained best.pt into the ROS vision package.")
    parser.add_argument("--weights", required=True, help="Path to trained best.pt.")
    parser.add_argument("--target", default=DEFAULT_TARGET, help="Target detector weight path.")
    parser.add_argument("--source-root", default=".", help="Root of the my_yolov11 workspace.")
    return parser.parse_args()


def resolve_path(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (root / path).resolve()


def main():
    args = parse_args()
    root = Path(args.source_root).expanduser().resolve()
    weights = resolve_path(root, args.weights)
    target = resolve_path(root, args.target)

    if not weights.exists():
        raise SystemExit(f"Weight file not found: {weights}")

    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = target.with_name(f"{target.stem}.backup_{stamp}{target.suffix}")
        shutil.copy2(target, backup)
        print(f"[copy] backup={backup}")

    shutil.copy2(weights, target)
    print(f"[copy] target={target}")


if __name__ == "__main__":
    main()
