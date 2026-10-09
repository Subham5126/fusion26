"""Explicit local-checkpoint training with finite loss/update/checkpoint evidence."""
import argparse
import csv
import importlib.metadata as metadata
import json
from pathlib import Path
from time import perf_counter

import yaml

from .common import fresh_output, runtime_setup, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("experiments/yolo/train.yaml"))
    for name in ("epochs", "imgsz", "batch", "seed"):
        parser.add_argument(f"--{name}", type=int)
    parser.add_argument("--device")
    parser.add_argument("--time-hours", type=float, default=.25, help="Soft wall-time budget checked at epoch boundaries; does not increase requested epochs")
    args = parser.parse_args()
    if not args.weights.is_file() or not args.data.is_file():
        raise ValueError("Provide existing local checkpoint and prepared YAML; no automatic model/dataset download")
    data_config = yaml.safe_load(args.data.read_text())
    if "download" in data_config or data_config.get("nc") != 1 or data_config.get("names") != {0: "streak"}:
        raise ValueError("Use prepared one-class streak configuration with no download directive")
    runtime_setup()
    import torch
    from ultralytics import YOLO
    torch.set_num_threads(2)
    output = fresh_output(args.output)
    config = yaml.safe_load(args.config.read_text())
    config.update({k: v for k, v in vars(args).items() if k in ("epochs", "imgsz", "batch", "seed", "device") and v is not None})
    config.update(data=str(args.data.resolve()), project=str(output), name="run", exist_ok=False)
    if config["epochs"] < 1 or config["batch"] < 1 or config["imgsz"] < 32 or args.time_hours <= 0:
        raise ValueError("Invalid bounded training settings")
    model = YOLO(str(args.weights.resolve()), task="detect")
    evidence = {"state": "started", "weights_sha256": sha256(args.weights), "data_sha256": sha256(args.data),
                "config": config, "packages": {n: metadata.version(n) for n in ("torch", "torchvision", "ultralytics")},
                "pretrained_loaded": True, "initial_checkpoint_names": model.names,
                "pretrained_parameter_count": sum(p.numel() for p in model.model.parameters()),
                "soft_time_budget_hours":args.time_hours}
    before = {}
    steps = []

    def on_start(trainer):
        # Capture after transfer-learning head reconstruction, before any updates.
        before.update({name: value.detach().cpu().clone() for name, value in trainer.model.named_parameters() if value.requires_grad})
        evidence["trained_class_names"]=trainer.model.names
        evidence["training_parameter_count"]=sum(p.numel() for p in trainer.model.parameters())

    def on_batch(trainer):
        loss = trainer.loss.detach().float().cpu()
        if not torch.isfinite(loss).all():
            raise ValueError("Nonfinite training loss")
        steps.append(float(loss.sum()))

    def on_epoch_end(trainer):
        if perf_counter()-started >= args.time_hours*3600:
            trainer.stop=True

    model.add_callback("on_train_start", on_start)
    model.add_callback("on_train_batch_end", on_batch)
    model.add_callback("on_train_epoch_end", on_epoch_end)
    write_json(output / "training_evidence.json", evidence)
    started = perf_counter()
    try:
        model.train(**config)
        trained = model.trainer
        after = dict(trained.model.named_parameters())
        changed = sum(name in after and not torch.equal(value, after[name].detach().cpu()) for name, value in before.items())
        best, last = Path(trained.best), Path(trained.last)
        if not steps or not changed or not best.is_file() or not last.is_file():
            raise ValueError("Training lacked finite steps, parameter updates or saved best/last checkpoints")
        with (trained.save_dir / "results.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        evidence.update(state="completed", elapsed_s=perf_counter()-started,
                        epochs_completed=len(rows), batches_checked=len(steps), loss_min=min(steps), loss_max=max(steps),
                        changed_parameter_tensors=changed, best=str(best), last=str(last),
                        best_sha256=sha256(best), last_sha256=sha256(last), final_csv_row=rows[-1],
                        validation_metrics=trained.metrics)
    except Exception as exc:
        evidence.update(state="failed", error=f"{type(exc).__name__}: {exc}", elapsed_s=perf_counter()-started)
        write_json(output / "training_evidence.json", evidence)
        raise
    write_json(output / "training_evidence.json", evidence)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
