"""Behavioral evidence for T14: data layout, safety, coordinates and label separation."""

from io import BytesIO
import json
from pathlib import Path
import stat
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import numpy as np
from PIL import Image
import pytest

from astrotrace.datasets import ArchiveLimits, DatasetError, SpotGeoDataset, inspect_zip, parse_annotations
from astrotrace.datasets.fixtures import create_fixture, zip_fixture
from astrotrace.datasets.visualization import overlay_sequence, save_overlay
from astrotrace.preprocessing.images import decode_png, display_uint8


@pytest.fixture
def sample(tmp_path):
    return create_fixture(tmp_path / "sample")


def records(coords=None):
    points = [[12.125, 7.875]] if coords is None else coords
    return [{"sequence_id": 1, "frame": i, "num_objects": len(points), "object_coords": points}
            for i in range(1, 6)]


def png(pixels):
    stream = BytesIO()
    Image.fromarray(pixels).save(stream, format="PNG")
    return stream.getvalue()


def test_directory_and_wrapped_zip_load_identical_ordered_images(sample, tmp_path):
    path = zip_fixture(sample, tmp_path / "fixture.zip", prefix="SpotGEOv2")
    directory = SpotGeoDataset(sample, expected_size=(64, 48))
    zipped = SpotGeoDataset(path, expected_size=(64, 48))
    assert zipped.prefix == "SpotGEOv2"
    assert directory.sequence_ids == zipped.sequence_ids == ("1", "2")
    a, b = directory.load_sequence(1), zipped.load_sequence("1")
    for index, (left, right) in enumerate(zip(a.frames, b.frames)):
        assert left.frame_index == index and left.official_frame == index + 1
        assert left.timestamp_s is None
        assert (left.width_px, left.height_px) == (64, 48)
        assert left.pixels.dtype == np.uint8 and not left.pixels.flags.writeable
        np.testing.assert_array_equal(left.pixels, right.pixels)
    assert not hasattr(a, "annotations")


def test_fixture_is_reproducible_with_separate_labels(sample, tmp_path):
    other = create_fixture(tmp_path / "other")
    for path in sample.rglob("*"):
        if path.is_file():
            assert path.read_bytes() == (other / path.relative_to(sample)).read_bytes()
    with pytest.raises(FileExistsError):
        create_fixture(sample)


def test_official_size_layout(tmp_path):
    folder = tmp_path / "train" / "1224"
    folder.mkdir(parents=True)
    for frame in range(1, 6):
        Image.new("L", (640, 480), frame).save(folder / f"{frame}.png")
    sequence = SpotGeoDataset(tmp_path).load_sequence(1224)
    assert [f.pixels[100, 500] for f in sequence.frames] == [1, 2, 3, 4, 5]


def test_inference_zip_reads_images_only_even_with_corrupt_labels(sample, tmp_path, monkeypatch):
    (sample / "train_anno.json").write_text("invalid annotation JSON", encoding="utf-8")
    archive = zip_fixture(sample, tmp_path / "fixture.zip")
    opened = []
    real_open = ZipFile.open

    def observe(self, name, *args, **kwargs):
        opened.append(name.filename if isinstance(name, ZipInfo) else name)
        return real_open(self, name, *args, **kwargs)

    monkeypatch.setattr(ZipFile, "open", observe)
    SpotGeoDataset(archive, expected_size=(64, 48)).load_sequence(1)
    assert opened == [f"train/1/{i}.png" for i in range(1, 6)]


def test_inspector_does_not_open_payloads(sample, tmp_path, monkeypatch):
    archive = zip_fixture(sample, tmp_path / "fixture.zip")

    def fail(*args, **kwargs):
        pytest.fail("Inventory attempted to decompress a payload")

    monkeypatch.setattr(ZipFile, "open", fail)
    inventory = inspect_zip(archive)
    assert len([e for e in inventory.entries if e.kind == "image"]) == 10
    assert "train_anno.json" in [e.name for e in inventory.entries if e.kind == "annotation"]
    assert not (tmp_path / "train").exists()


@pytest.mark.parametrize("name", ["../escape.png", "/abs.png", "C:/x.png", "a\\b.png", "a/../b.png",
                                 "a//b.png", "./b.png", "CON.png", "train/1/1.png "])
def test_unsafe_zip_names_rejected(tmp_path, name):
    path = tmp_path / "unsafe.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr(name, b"anything")
    if "\\" in name:
        # ZipInfo normalizes separators when authoring on Windows. Replace both
        # local and central names to exercise an actually unsafe external ZIP.
        path.write_bytes(path.read_bytes().replace(b"a/b.png", b"a\\b.png"))
    with pytest.raises(DatasetError, match="Unsafe"):
        inspect_zip(path)


def test_symlink_zip_rejected(tmp_path):
    path = tmp_path / "unsafe.zip"
    member = ZipInfo("train/1/1.png")
    member.create_system = 3
    member.external_attr = (stat.S_IFLNK | 0o777) << 16
    with ZipFile(path, "w") as archive:
        archive.writestr(member, "elsewhere")
    with pytest.raises(DatasetError, match="special"):
        inspect_zip(path)


def test_duplicate_case_names_rejected(tmp_path):
    path = tmp_path / "duplicate.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("train/1/1.png", b"a")
        archive.writestr("TRAIN/1/1.PNG", b"b")
    with pytest.raises(DatasetError, match="case-aliased"):
        inspect_zip(path)


@pytest.mark.parametrize("limits", [ArchiveLimits(max_entries=1), ArchiveLimits(max_central_directory_bytes=1),
                                   ArchiveLimits(max_member_bytes=1), ArchiveLimits(max_total_uncompressed_bytes=1),
                                   ArchiveLimits(max_compression_ratio=0.5)])
def test_zip_metadata_limits(sample, tmp_path, limits):
    path = zip_fixture(sample, tmp_path / "fixture.zip")
    with pytest.raises(DatasetError, match="limit"):
        inspect_zip(path, limits)


def test_high_ratio_zip_rejected(tmp_path):
    path = tmp_path / "bomb.zip"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("huge.json", b"0" * 2_000_000)
    with pytest.raises(DatasetError, match="compression ratio"):
        inspect_zip(path)


def test_corrupt_archive_rejected(tmp_path):
    path = tmp_path / "broken.zip"
    path.write_bytes(b"not a ZIP")
    with pytest.raises(DatasetError):
        inspect_zip(path)


def test_zip_payload_crc_is_checked_on_read(sample, tmp_path):
    path = zip_fixture(sample, tmp_path / "corrupt.zip")
    with ZipFile(path) as archive:
        entry = archive.getinfo("train/1/1.png")
    payload = bytearray(path.read_bytes())
    offset = entry.header_offset
    name_length = int.from_bytes(payload[offset + 26:offset + 28], "little")
    extra_length = int.from_bytes(payload[offset + 28:offset + 30], "little")
    payload_start = offset + 30 + name_length + extra_length
    payload[payload_start + entry.compress_size // 2] ^= 0xFF
    path.write_bytes(payload)
    # Inventory is metadata-only; the selected payload read detects corruption.
    assert inspect_zip(path).entries
    with pytest.raises(DatasetError):
        SpotGeoDataset(path, expected_size=(64, 48)).load_sequence(1)


def test_ambiguous_zip_prefix_requires_explicit_selection(sample, tmp_path):
    path = tmp_path / "ambiguous.zip"
    with ZipFile(path, "w") as archive:
        for prefix in ("a", "b"):
            for image in (sample / "train" / "1").iterdir():
                archive.write(image, f"{prefix}/train/1/{image.name}")
    with pytest.raises(DatasetError, match="ambiguous"):
        SpotGeoDataset(path, expected_size=(64, 48))
    assert SpotGeoDataset(path, prefix="b", expected_size=(64, 48)).load_sequence(1).sequence_id == "1"


@pytest.mark.parametrize("bad_id", [True, "../1", "01", "0", -1, 1.5, "https://example.org"])
def test_invalid_sequence_id(sample, bad_id):
    with pytest.raises(DatasetError):
        SpotGeoDataset(sample, expected_size=(64, 48)).load_sequence(bad_id)


def test_missing_unknown_and_extra_frame(sample):
    with pytest.raises(DatasetError, match="Unknown"):
        SpotGeoDataset(sample, expected_size=(64, 48)).load_sequence(999)
    (sample / "train/1/5.png").unlink()
    with pytest.raises(DatasetError, match="exactly frames"):
        SpotGeoDataset(sample, expected_size=(64, 48))
    Image.new("L", (64, 48)).save(sample / "train/1/6.png")
    with pytest.raises(DatasetError, match="filename"):
        SpotGeoDataset(sample, expected_size=(64, 48))


def test_empty_dataset_and_bad_split(tmp_path):
    (tmp_path / "train").mkdir()
    with pytest.raises(DatasetError, match="No five-frame"):
        SpotGeoDataset(tmp_path)
    with pytest.raises(DatasetError, match="split"):
        SpotGeoDataset(tmp_path, split="../ground_truth")


def test_image_dimensions_and_byte_limits(sample):
    with pytest.raises(DatasetError, match="Expected image size"):
        SpotGeoDataset(sample).load_sequence(1)
    with pytest.raises(DatasetError, match="pixel limit"):
        SpotGeoDataset(sample, expected_size=None, max_pixels=50).load_sequence(1)
    with pytest.raises(DatasetError, match="byte limit"):
        SpotGeoDataset(sample, expected_size=None, max_image_bytes=10).load_sequence(1)
    Image.new("L", (63, 48)).save(sample / "train/1/3.png")
    with pytest.raises(DatasetError, match="dimensions differ"):
        SpotGeoDataset(sample, expected_size=None).load_sequence(1)


@pytest.mark.parametrize("payload", [b"broken PNG", png(np.zeros((48, 64, 3), dtype=np.uint8))])
def test_bad_image_inputs(payload):
    with pytest.raises(ValueError):
        decode_png(payload, expected_size=(64, 48))


def test_size_guard_precedes_image_allocation(monkeypatch):
    payload = png(np.zeros((48, 64), dtype=np.uint8))

    def fail(*args, **kwargs):
        pytest.fail("Oversized image was loaded before bounds were checked")

    monkeypatch.setattr(Image.Image, "load", fail)
    with pytest.raises(ValueError, match="pixel limit"):
        decode_png(payload, max_pixels=100, expected_size=None)


def test_non_png_truncated_and_animated_inputs():
    stream = BytesIO()
    Image.new("L", (64, 48)).save(stream, format="JPEG")
    with pytest.raises(ValueError, match="grayscale PNG"):
        decode_png(stream.getvalue(), expected_size=(64, 48))
    stream = BytesIO()
    Image.new("L", (64, 48), 0).save(stream, format="PNG", save_all=True,
                                     append_images=[Image.new("L", (64, 48), 255)])
    with pytest.raises(ValueError, match="Animated"):
        decode_png(stream.getvalue(), expected_size=(64, 48))
    with pytest.raises(ValueError):
        decode_png(png(np.arange(3072, dtype=np.uint16).reshape(48, 64))[:50], expected_size=(64, 48))


def test_uint16_and_display_do_not_change_original():
    pixels = np.array([[0, 1000], [32000, 65535]], dtype=np.uint16)
    decoded = decode_png(png(pixels), expected_size=(2, 2))
    np.testing.assert_array_equal(decoded, pixels)
    assert decoded.dtype == np.uint16
    assert display_uint8(decoded)[1, 1] == 255
    np.testing.assert_array_equal(decoded, pixels)
    assert not display_uint8(np.zeros((2, 2), dtype=np.uint8)).any()


def test_empty_annotations_and_missing_are_distinct():
    assert not parse_annotations("[]").frames
    labels = parse_annotations(json.dumps(records([])))
    assert all(frame.num_objects == 0 for frame in labels.for_sequence(1))
    with pytest.raises(DatasetError, match="Missing"):
        labels.for_sequence(2)
    with pytest.raises(DatasetError, match="Missing"):
        parse_annotations(json.dumps(records([])[:-1]))


def test_fractional_xy_boundary_and_original_id_preserved():
    coords = [[-0.5, -0.5], [639.5, 479.5], [12.125, 7.875]]
    data = records(coords)
    data[0]["sequence_id"] = "1"
    labels = parse_annotations(json.dumps(data))
    first = labels.for_sequence(1)[0]
    assert first.original_sequence_id == "1" and first.frame_index == 0
    assert first.object_coords == tuple(map(tuple, coords))


@pytest.mark.parametrize("point", [[-0.5001, 0], [639.5001, 0], [0, 479.5001], [0, -0.5001],
                                  [True, 2], ["1", 2], [1], [1, 2, 3], [float("nan"), 0],
                                  [float("inf"), 0], [1e309, 0]])
def test_bad_coordinates_rejected(point):
    with pytest.raises(DatasetError):
        parse_annotations(json.dumps(records([point])))


@pytest.mark.parametrize("mutation", [lambda r: r.update(frame=0), lambda r: r.update(frame=6),
                                     lambda r: r.update(frame=True), lambda r: r.update(num_objects=True),
                                     lambda r: r.update(num_objects=2), lambda r: r.update(sequence_id="../1"),
                                     lambda r: r.update(extra="bad"), lambda r: r.pop("object_coords")])
def test_bad_annotation_record(mutation):
    data = records()
    mutation(data[0])
    with pytest.raises(DatasetError):
        parse_annotations(json.dumps(data))


@pytest.mark.parametrize("payload", ["{}", "not json", b"\xff", "[null]",
                                    '[{"sequence_id":1,"sequence_id":2}]'])
def test_malformed_json(payload):
    with pytest.raises(DatasetError):
        parse_annotations(payload)


def test_duplicate_incomplete_inconsistent_and_oversized_annotations():
    data = records()
    with pytest.raises(DatasetError, match="Duplicate annotation"):
        parse_annotations(json.dumps(data + data[:1]))
    with pytest.raises(DatasetError, match="byte limit"):
        parse_annotations(json.dumps(data), max_bytes=10)
    data[0].update(num_objects=0, object_coords=[])
    with pytest.raises(DatasetError, match="Inconsistent"):
        parse_annotations(json.dumps(data))
    partial = parse_annotations(json.dumps(data[:1]), require_complete=False)
    with pytest.raises(DatasetError, match="Missing"):
        partial.for_sequence(1)


def test_overlay_xy_direction_no_shift_and_no_mutation(sample, tmp_path):
    sequence = SpotGeoDataset(sample, expected_size=(64, 48)).load_sequence(1)
    before = sequence.frames[0].pixels.copy()
    coords = [[40.0, 10.0]]
    labels = parse_annotations(json.dumps(records(coords)), width_px=64, height_px=48)
    overlay = overlay_sequence(sequence, labels)
    # First panel begins at y=56; ensure x/y were neither swapped nor shifted.
    assert overlay.getpixel((40, 56 + 10)) == (255, 69, 69)
    assert overlay.getpixel((10, 56 + 40)) != (255, 69, 69)
    np.testing.assert_array_equal(sequence.frames[0].pixels, before)
    output = save_overlay(sequence, labels, tmp_path / "overlay.png")
    assert Image.open(output).size == (352, 104)
    with pytest.raises(FileExistsError):
        save_overlay(sequence, labels, output)
    with pytest.raises(DatasetError, match="dimensions"):
        overlay_sequence(sequence, parse_annotations(json.dumps(records())))


def test_bounded_annotation_reads_and_local_traversal(sample, tmp_path):
    directory = SpotGeoDataset(sample, expected_size=(64, 48))
    for name in ("../secret.json", "/absolute.json", "C:/secret.json"):
        with pytest.raises(DatasetError):
            directory.read_file(name, max_bytes=1024)
    zipped = SpotGeoDataset(zip_fixture(sample, tmp_path / "sample.zip"), expected_size=(64, 48))
    for dataset in (directory, zipped):
        with pytest.raises(DatasetError):
            dataset.read_file("train_anno.json", max_bytes=10)
        labels = parse_annotations(dataset.read_file("train_anno.json", max_bytes=10000), width_px=64, height_px=48)
        assert labels.for_sequence(2)[0].object_coords == ()


def test_cli_fixture_inventory_and_overlay(tmp_path):
    script = Path(__file__).resolve().parents[2] / "scripts/spotgeo.py"
    root, archive, overlay = tmp_path / "sample", tmp_path / "sample.zip", tmp_path / "overlay.png"
    commands = [
        ["fixture", str(root), "--zip", str(archive)],
        ["inspect", str(archive), "--limit", "2", "--sha256"],
        ["list", str(archive), "--fixture-size"],
        ["view", str(archive), "--fixture-size", "--sequence", "1", "--annotations", "train_anno.json", "--output", str(overlay)],
    ]
    for command in commands:
        result = subprocess.run([sys.executable, str(script), *command], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        assert isinstance(json.loads(result.stdout), dict)
    assert overlay.exists()
    failed = subprocess.run([sys.executable, str(script), "inspect", str(tmp_path / "missing.zip")],
                            capture_output=True, text=True, timeout=30)
    assert failed.returncode == 2 and "spotgeo:" in failed.stderr
