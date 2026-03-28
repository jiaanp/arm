#!/usr/bin/env python3
import argparse
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Train a custom YOLO11 detector.")
    parser.add_argument("--source-root", default=".", help="Root of the my_yolov11 workspace.")
    parser.add_argument("--data", default="configs/cube_detect.yaml", help="Dataset yaml path.")
    parser.add_argument("--model", default="yolo11n.pt", help="Base model or checkpoint path.")
    parser.add_argument("--project", default="runs/detect", help="Training output directory.")
    parser.add_argument("--name", default="cube_detect", help="Run name.")
    parser.add_argument("--imgsz", type=int, default=640, help="Training image size.")
    parser.add_argument("--epochs", type=int, default=100, help="Number of epochs.")
    parser.add_argument("--batch", type=int, default=16, help="Batch size.")
    parser.add_argument("--device", default="", help="CUDA device id or cpu.")
    parser.add_argument("--workers", type=int, default=8, help="Dataloader workers.")
    parser.add_argument("--patience", type=int, default=30, help="Early stop patience.")
    parser.add_argument("--cache", action="store_true", help="Enable dataset cache.")
    parser.add_argument("--exist-ok", action="store_true", help="Allow reusing output dir.")
    return parser.parse_args()


def resolve_path(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (root / path).resolve()


def main():
    args = parse_args()

    try:
        from ultralytics import YOLO
    except ModuleNotFoundError as exc:
        raise SystemExit("ultralytics is not installed. Run: pip install ultralytics") from exc

    root = Path(args.source_root).expanduser().resolve()
    data_path = resolve_path(root, args.data)
    project_path = resolve_path(root, args.project)

    if not data_path.exists():
        raise SystemExit(f"Dataset yaml not found: {data_path}")

    model_arg = args.model
    model_path = Path(model_arg).expanduser()
    if not model_path.is_absolute():
        candidate = (root / model_arg).resolve()
        if candidate.exists():
            model_arg = str(candidate)

    project_path.mkdir(parents=True, exist_ok=True)

    print(f"[train] root={root}")
    print(f"[train] data={data_path}")
    print(f"[train] model={model_arg}")
    print(f"[train] project={project_path}")
    print(f"[train] name={args.name}")

    model = YOLO(model_arg)
    model.train(
        data=str(data_path),
        imgsz=args.imgsz,
        epochs=args.epochs,
        batch=args.batch,
        project=str(project_path),
        name=args.name,
        device=args.device,
        workers=args.workers,
        patience=args.patience,
        cache=args.cache,
        exist_ok=args.exist_ok,
    )

    trainer = getattr(model, "trainer", None)
    if trainer is not None:
        best = getattr(trainer, "best", None)
        last = getattr(trainer, "last", None)
        if best:
            print(f"[train] best={best}")
        if last:
            print(f"[train] last={last}")


if __name__ == "__main__":
    main()
