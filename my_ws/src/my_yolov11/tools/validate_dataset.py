#!/usr/bin/env python3
import argparse
from pathlib import Path


IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}


def parse_args():
    parser = argparse.ArgumentParser(description='Validate YOLO detection labels before training.')
    parser.add_argument('--source-root', default='.')
    parser.add_argument('--images', default='raw/images')
    parser.add_argument('--labels', default='raw/labels')
    parser.add_argument('--num-classes', type=int, default=1)
    return parser.parse_args()


def resolve_path(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (root / path).resolve()


def validate_label_line(line: str, path: Path, line_no: int, num_classes: int, errors: list[str]):
    parts = line.strip().split()
    if len(parts) != 5:
        errors.append(f'{path}:{line_no} expected 5 fields, got {len(parts)}')
        return

    try:
        cls_id = int(float(parts[0]))
        vals = [float(x) for x in parts[1:]]
    except ValueError:
        errors.append(f'{path}:{line_no} contains non-numeric values')
        return

    if cls_id < 0 or cls_id >= num_classes:
        errors.append(f'{path}:{line_no} class id {cls_id} out of range [0, {num_classes - 1}]')

    x_center, y_center, width, height = vals
    for name, value in [('x_center', x_center), ('y_center', y_center), ('width', width), ('height', height)]:
        if value < 0.0 or value > 1.0:
            errors.append(f'{path}:{line_no} {name}={value} outside [0, 1]')
    if width <= 0.0 or height <= 0.0:
        errors.append(f'{path}:{line_no} width/height must be > 0')


def main():
    args = parse_args()
    root = Path(args.source_root).expanduser().resolve()
    images_dir = resolve_path(root, args.images)
    labels_dir = resolve_path(root, args.labels)

    if not images_dir.exists():
        raise SystemExit(f'images dir not found: {images_dir}')
    if not labels_dir.exists():
        raise SystemExit(f'labels dir not found: {labels_dir}')

    images = sorted([p for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS])
    labels = sorted([p for p in labels_dir.iterdir() if p.is_file() and p.suffix.lower() == '.txt'])
    if not images:
        raise SystemExit(f'no images found in {images_dir}')

    image_stems = {p.stem for p in images}
    label_stems = {p.stem for p in labels}

    missing_labels = sorted(image_stems - label_stems)
    missing_images = sorted(label_stems - image_stems)
    errors = []

    for label_path in labels:
        with label_path.open('r', encoding='utf-8') as f:
            for line_no, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                validate_label_line(line, label_path, line_no, args.num_classes, errors)

    print(f'[validate] images={len(images)} labels={len(labels)}')
    print(f'[validate] matched={len(image_stems & label_stems)}')

    if missing_labels:
        print('[validate] missing labels for images:')
        for name in missing_labels[:50]:
            print(f'  - {name}')
        if len(missing_labels) > 50:
            print(f'  ... and {len(missing_labels) - 50} more')

    if missing_images:
        print('[validate] missing images for labels:')
        for name in missing_images[:50]:
            print(f'  - {name}')
        if len(missing_images) > 50:
            print(f'  ... and {len(missing_images) - 50} more')

    if errors:
        print('[validate] label format errors:')
        for err in errors[:100]:
            print(f'  - {err}')
        if len(errors) > 100:
            print(f'  ... and {len(errors) - 100} more')
        raise SystemExit(1)

    if missing_labels or missing_images:
        raise SystemExit(1)

    print('[validate] dataset looks good')


if __name__ == '__main__':
    main()
