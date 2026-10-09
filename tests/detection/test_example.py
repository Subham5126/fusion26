"""Installed evidence runner must read Git from the caller's repository."""

from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from orbittrace.detection import example


def test_tracking_snapshot_uses_repository_cwd_when_module_is_installed(tmp_path, monkeypatch):
    source = tmp_path / "raw"
    sequence = source / "train" / "1"
    sequence.mkdir(parents=True)
    for index in range(1, 6):
        Image.fromarray(np.zeros((480, 640), dtype=np.uint8)).save(sequence / f"{index}.png")
    monkeypatch.chdir(tmp_path)
    # A wheel's module lives in site-packages, outside the Git repository.
    monkeypatch.setattr(example, "__file__", str(tmp_path / "environment/Lib/site-packages/orbittrace/detection/example.py"))

    class SnapshotReached(Exception):
        pass

    def snapshot(root, ref, output):
        assert root == Path.cwd()
        assert ref == "test-local-ref"
        assert output == tmp_path / "report"
        raise SnapshotReached

    monkeypatch.setattr(example, "_load_snapshot", snapshot)
    with pytest.raises(SnapshotReached):
        example.main(["--source", str(source), "--sequence", "1",
                      "--output", str(tmp_path / "report"), "--tracking-ref", "test-local-ref"])
