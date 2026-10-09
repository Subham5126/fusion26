"""Small portable IO helpers. Generated outputs must be outside source paths."""
import hashlib
import json
import os
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def runtime_setup():
    # Must precede importing Ultralytics; prevent auto-installs and external loggers.
    root = Path(os.environ.get("CV_T15_CACHE", ".cache/cv_t15")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    config_dir=root/"ultralytics"
    (config_dir/"Ultralytics").mkdir(parents=True,exist_ok=True)
    os.environ["YOLO_CONFIG_DIR"] = str(config_dir)
    os.environ["YOLO_AUTOINSTALL"] = "false"
    os.environ.setdefault("WANDB_DISABLED", "true")
    from ultralytics import settings
    settings.update({"sync": False, "wandb": False, "mlflow": False, "comet": False,
                     "clearml": False, "tensorboard": False, "dvc": False, "raytune": False})
    return root


def fresh_output(path):
    path = Path(path).resolve()
    # Source must not receive model runs/datasets; enforce even outside this repo.
    if "experiments" in path.parts or "tests" in path.parts:
        raise ValueError("Store generated output in an artifact/cache directory")
    path.mkdir(parents=True, exist_ok=False)
    return path
