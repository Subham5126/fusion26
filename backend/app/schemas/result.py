"""Scientific output contracts. Fixture validity does not imply a pipeline run."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .base import ContractModel, Finite, NonNegative, OpaqueId, Profile, Quality, SourceType, TimeBasis, Version

PixelPair = tuple[Finite, Finite]
Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class Detection(ContractModel):
    detection_id: OpaqueId
    frame_index: Annotated[int, Field(ge=0)]
    x_raw_px: Finite
    y_raw_px: Finite
    bbox_raw_px: tuple[NonNegative, NonNegative, NonNegative, NonNegative]
    kind: Literal["compact", "streak", "unknown"]
    quality_score: Quality
    detector_name: str
    x_reference_px: Finite | None = None
    y_reference_px: Finite | None = None
    endpoints_raw_px: tuple[PixelPair, PixelPair] | None = None
    evidence_statistics: dict[str, Finite | None] | None = None

    @model_validator(mode="after")
    def coordinates(self):
        x0, y0, x1, y1 = self.bbox_raw_px
        if not (x0 <= self.x_raw_px < x1 and y0 <= self.y_raw_px < y1):
            raise ValueError("Centroid must lie inside the exclusive-upper-bound box")
        if (self.x_reference_px is None) != (self.y_reference_px is None):
            raise ValueError("Reference coordinates must be supplied together")
        return self


class TrackPoint(ContractModel):
    frame_index: Annotated[int, Field(ge=0)]
    timestamp_s: Finite | None = None
    x_reference_px: Finite
    y_reference_px: Finite
    x_raw_px: Finite | None = None
    y_raw_px: Finite | None = None
    point_type: Literal["observed", "interpolated", "extrapolated"]
    detection_id: OpaqueId | None = None
    out_of_field: bool | None = None

    @model_validator(mode="after")
    def observation_identity(self):
        if (self.point_type == "observed") != (self.detection_id is not None):
            raise ValueError("Only observed points must reference a real detection")
        if (self.x_raw_px is None) != (self.y_raw_px is None):
            raise ValueError("Raw coordinates must be supplied together")
        return self


class Trajectory(ContractModel):
    model: Literal["constant_velocity"]
    coordinate_frame: OpaqueId
    time_basis: TimeBasis
    vx: Finite
    vy: Finite
    speed: NonNegative
    speed_unit: Literal["px/frame", "px/s"]
    fit_rmse_px: NonNegative | None
    observations_used: Annotated[int, Field(ge=3)]
    reference_epoch: Finite
    x_at_epoch_px: Finite
    y_at_epoch_px: Finite
    predictions: list[TrackPoint]

    @model_validator(mode="after")
    def units_and_predictions(self):
        expected = "px/frame" if self.time_basis == "frame" else "px/s"
        if self.speed_unit != expected:
            raise ValueError("Speed unit must agree with time basis")
        if any(p.point_type != "extrapolated" for p in self.predictions):
            raise ValueError("Trajectory predictions must be extrapolated")
        return self


class Track(ContractModel):
    track_id: OpaqueId
    status: Literal["tentative", "confirmed", "ended"]
    candidate_label: Literal["orbital-object candidate; identity unverified"]
    points: list[TrackPoint]
    observed_count: Annotated[int, Field(ge=0)]
    quality_score: Quality
    warnings: list[str]
    trajectory: Trajectory | None

    @model_validator(mode="after")
    def observed_support(self):
        observations = [p for p in self.points if p.point_type == "observed"]
        if self.observed_count != len(observations):
            raise ValueError("observed_count must count only observed points")
        indexes = [p.frame_index for p in self.points]
        if indexes != sorted(set(indexes)):
            raise ValueError("Track points must be ordered and unique by frame")
        if self.status == "confirmed" and self.observed_count < 3:
            raise ValueError("Confirmation requires at least three observations")
        if self.trajectory and self.trajectory.observations_used > self.observed_count:
            raise ValueError("Fit cannot use more observations than the track contains")
        return self


class RegistrationResult(ContractModel):
    status: Literal["identity", "estimated", "failed", "not_required"]
    warnings: list[str]


class Provenance(ContractModel):
    input_sha256: Hash | None
    config_sha256: Hash | None
    code_commit: str | None
    dataset_version: str | None


class BenchmarkMetrics(ContractModel):
    benchmark_id: OpaqueId
    split: Literal["development", "validation", "test"]
    matching_gate_px: NonNegative
    tp: Annotated[int, Field(ge=0)]
    fp: Annotated[int, Field(ge=0)]
    fn: Annotated[int, Field(ge=0)]
    precision: Quality | None
    recall: Quality | None
    localization_rmse_px: NonNegative | None
    null_reasons: dict[str, str]


class AnalysisResult(ContractModel):
    schema_version: Version
    job_id: OpaqueId
    sequence_id: OpaqueId
    source_type: SourceType
    profile: Profile
    status: Literal["succeeded"]
    time_basis: TimeBasis
    coordinate_frame: OpaqueId
    registration: RegistrationResult
    detections: list[Detection]
    tracks: list[Track]
    metrics: BenchmarkMetrics | None
    runtime_ms: NonNegative | None
    warnings: list[str]
    provenance: Provenance

    @model_validator(mode="after")
    def references(self):
        detections = {d.detection_id: d for d in self.detections}
        if len(detections) != len(self.detections):
            raise ValueError("Detection IDs must be unique")
        if len({t.track_id for t in self.tracks}) != len(self.tracks):
            raise ValueError("Track IDs must be unique")
        assigned = set()
        for track in self.tracks:
            for point in track.points:
                if point.point_type == "observed":
                    detection = detections.get(point.detection_id)
                    if detection is None or detection.frame_index != point.frame_index:
                        raise ValueError("Observed point must reference a same-frame detection")
                    if point.detection_id in assigned:
                        raise ValueError("A detection cannot support multiple track points")
                    assigned.add(point.detection_id)
            if track.trajectory and (track.trajectory.time_basis != self.time_basis or
                                     track.trajectory.coordinate_frame != self.coordinate_frame):
                raise ValueError("Trajectory must use the result coordinate frame and time basis")
        points = [p for t in self.tracks for p in t.points]
        points += [p for t in self.tracks if t.trajectory for p in t.trajectory.predictions]
        if any((p.timestamp_s is not None) != (self.time_basis == "second") for p in points):
            raise ValueError("Point timestamps must agree with result time basis")
        return self
