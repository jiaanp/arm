#!/usr/bin/env python3
import argparse
import random
import shutil
from pathlib import Path


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args():
    parser = argparse.ArgumentParser(description="Split raw YOLO data into train/val folders.")
    parser.add_argument("--source-root", default=".", help="Root of the my_yolov11 workspace.")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="Validation ratio in [0, 1).")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument("--clear", action="store_true", help="Clear existing split folders before copying.")
    return parser.parse_args()


def clear_dir(path: Path):
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_file() or child.is_symlink():
            child.unlink()


def main():
    args = parse_args()
    root = Path(args.source_root).expanduser().resolve()

    raw_images = root / "raw" / "images"
    raw_labels = root / "raw" / "labels"
    train_images = root / "dataset" / "images" / "train"
    val_images = root / "dataset" / "images" / "val"
    train_labels = root / "dataset" / "labels" / "train"
    val_labels = root / "dataset" / "labels" / "val"

    for path in [raw_images, raw_labels, train_images, val_images, train_labels, val_labels]:
        path.mkdir(parents=True, exist_ok=True)

    if args.clear:
        for path in [train_images, val_images, train_labels, val_labels]:
            clear_dir(path)

    image_paths = sorted([p for p in raw_images.iterdir() if p.suffix.lower() in IMAGE_EXTS and p.is_file()])
    pairs = []
    missing_labels = []

    for image_path in image_paths:
        label_path = raw_labels / f"{image_path.stem}.txt"
        if label_path.exists():
            pairs.append((image_path, label_path))
        else:
            missing_labels.append(image_path.name)

    if missing_labels:
        print("[split] missing labels for:")
        for name in missing_labels:
            print(f"  - {name}")

    if not pairs:
        raise SystemExit("No matched image/label pairs found under raw/images and raw/labels.")

    rng = random.Random(args.seed)
    rng.shuffle(pairs)

    val_count = int(len(pairs) * args.val_ratio)
    val_pairs = pairs[:val_count]
    train_pairs = pairs[val_count:]

    if not train_pairs:
        raise SystemExit("Train split is empty. Reduce --val-ratio.")

    for image_path, label_path in train_pairs:
        shutil.copy2(image_path, train_images / image_path.name)
        shutil.copy2(label_path, train_labels / label_path.name)

    for image_path, label_path in val_pairs:
        shutil.copy2(image_path, val_images / image_path.name)
        shutil.copy2(label_path, val_labels / label_path.name)

    print(f"[split] total={len(pairs)} train={len(train_pairs)} val={len(val_pairs)}")
    print(f"[split] train_images={train_images}")
    print(f"[split] val_images={val_images}")


if __name__ == "__main__":
    main()
