"""Image-only, deterministic translation to frame 0 with explicit failures.

Images/metadata only: no labels or detector proposals enter transform estimation.
Matrices map native raw (x,y,1) to reference_frame_0. See REGISTRATION.md.
"""

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import math
from time import perf_counter

import cv2
import numpy as np

from .candidates import normalize_grayscale, robust_sigma


@dataclass(frozen=True)
class RegistrationConfig:
    max_features: int = 300
    min_inliers: int = 12
    feature_distance_px: float = 12.0
    feature_snr: float = 6.0
    forward_backward_px: float = 1.0
    inlier_radius_px: float = 1.25
    min_inlier_ratio: float = 0.6
    max_validation_rmse_px: float = 0.8
    min_phase_response: float = 0.1
    max_shift_px: float = 250.0
    min_axis_coverage: float = 0.2
    min_overlap: float = 0.45
    neighbor_retry: int = 1
    retry_flow_window_px: int = 21

    def __post_init__(self):
        for name, value in asdict(self).items():
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite numeric")
        if type(self.max_features) is not int or not 20 <= self.max_features <= 1000:
            raise ValueError("max_features must be an integer in 20..1000")
        if type(self.min_inliers) is not int or not 6 <= self.min_inliers <= self.max_features:
            raise ValueError("min_inliers must be an integer in 6..max_features")
        if type(self.neighbor_retry) is not int or self.neighbor_retry not in (0, 1):
            raise ValueError("neighbor_retry must be 0 or 1")
        if (type(self.retry_flow_window_px) is not int or not 15 <= self.retry_flow_window_px <= 35
                or self.retry_flow_window_px % 2 != 1):
            raise ValueError("retry_flow_window_px must be an odd integer in 15..35")
        for name in ('feature_distance_px', 'feature_snr', 'forward_backward_px',
                     'inlier_radius_px', 'max_validation_rmse_px', 'max_shift_px'):
            if not 0 < getattr(self, name) <= 1000:
                raise ValueError(f"{name} must be positive and <=1000")
        for name in ('min_inlier_ratio', 'min_phase_response', 'min_axis_coverage', 'min_overlap'):
            if not 0 < getattr(self, name) <= 1:
                raise ValueError(f"{name} must be in (0,1]")

    @classmethod
    def from_mapping(cls, value=None):
        if value is None:
            return cls()
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping) or set(value) - set(cls.__dataclass_fields__):
            raise ValueError("Expected declared registration config; no paths/truth keys")
        return cls(**value)


@dataclass(frozen=True)
class FrameRegistration:
    frame_index: int
    status: str
    raw_to_reference: tuple[tuple[float, ...], ...] | None
    reference_to_raw: tuple[tuple[float, ...], ...] | None
    phase_response: float | None
    reference_features: int
    matched_features: int
    fit_inliers: int
    fit_inlier_ratio: float | None
    validation_matches: int
    validation_inliers: int
    validation_inlier_ratio: float | None
    fit_rmse_px: float | None
    validation_rmse_px: float | None
    before_rmse_px: float | None
    axis_coverage: tuple[float, float] | None
    overlap_fraction: float | None
    runtime_ms: float
    warnings: tuple[str, ...]
    reference_points: tuple[tuple[float, float], ...] = ()
    raw_points: tuple[tuple[float, float], ...] = ()
    inlier_flags: tuple[bool, ...] = ()
    validation_flags: tuple[bool, ...] = ()
    initialization: str = 'phase_correlation'
    seed_frame_index: int | None = None
    flow_window_px: int = 25
    direct_failure_reasons: tuple[str, ...] = ()

    def transform_points(self, points, *, inverse=False):
        """Map finite Nx2 points; fail instead of fabricating identity on failure."""
        matrix = self.reference_to_raw if inverse else self.raw_to_reference
        if self.status == 'failed' or matrix is None:
            raise ValueError(f"Frame {self.frame_index} registration failed")
        points = np.asarray(points, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
            raise ValueError("Expected finite Nx2 (x,y) points")
        return points @ np.asarray(matrix)[:2, :2].T + np.asarray(matrix)[:2, 2]


@dataclass(frozen=True)
class SequenceRegistration:
    width_px: int
    height_px: int
    frames: tuple[FrameRegistration, ...]
    config: RegistrationConfig
    coordinate_frame: str = 'reference_frame_0'

    @property
    def status(self):
        return 'failed' if any(f.status == 'failed' for f in self.frames) else 'estimated'

    def to_dict(self):
        return {'model': 'translation', 'coordinate_frame': self.coordinate_frame,
                'transform_direction': 'raw_to_reference', 'units': 'px',
                'width_px': self.width_px, 'height_px': self.height_px,
                'status': self.status, 'config': asdict(self.config),
                'frames': [asdict(f) for f in self.frames]}


def _prepare(pixels, config):
    image, quantization = normalize_grayscale(pixels)
    if min(image.shape) < 32:
        raise ValueError("Registration requires dimensions >=32 pixels")
    response = (cv2.GaussianBlur(image, (0, 0), .8)
                - cv2.GaussianBlur(image, (0, 0), 8.0))
    noise = robust_sigma(response, quantization * .5)
    mask = (response > noise * config.feature_snr).astype(np.uint8) * 255
    margin = 14
    mask[:margin] = mask[-margin:] = 0
    mask[:, :margin] = mask[:, -margin:] = 0
    scale = max(float(np.percentile(response, 99.8)), noise * 12)
    view = np.rint(np.clip(response, 0, scale) * (255 / scale)).astype(np.uint8)
    return response, view, mask


def fit_translation(reference_points, raw_points, radius_px):
    """Deterministic exhaustive one-vector RANSAC, followed by median refinement.

    Each correspondence proposes a translation. Select maximum consensus, then
    smallest median residual, then original feature order. No random/global seed.
    Returns raw-to-reference shift and an inlier mask. Invalid pairs raise.
    """
    reference = np.asarray(reference_points, dtype=np.float64)
    raw = np.asarray(raw_points, dtype=np.float64)
    if (reference.shape != raw.shape or reference.ndim != 2 or reference.shape[1] != 2
            or not len(raw) or len(raw) > 1000 or not np.isfinite(reference).all()
            or not np.isfinite(raw).all() or type(radius_px) not in (int, float)
            or not math.isfinite(radius_px) or radius_px <= 0):
        raise ValueError("Expected 1..1000 finite corresponding Nx2 points and positive radius")
    shifts = reference - raw
    distances = np.linalg.norm(shifts[:, None] - shifts[None, :], axis=2)
    counts = (distances <= radius_px).sum(axis=1)
    tied = np.flatnonzero(counts == counts.max())
    best = min(tied, key=lambda i: (float(np.median(distances[i, distances[i] <= radius_px])), int(i)))
    shift = shifts[best]
    for _ in range(3):
        keep = np.linalg.norm(shifts - shift, axis=1) <= radius_px
        shift = np.median(shifts[keep], axis=0)
    return shift, np.linalg.norm(shifts - shift, axis=1) <= radius_px


def _matrix(shift):
    return ((1., 0., float(shift[0])), (0., 1., float(shift[1])), (0., 0., 1.))


def _match_translation(reference, view, moving_view, coarse, width, height, config, window_px=25):
    """Fit directly to frame 0; reserved points and all acceptance gates apply."""
    diagnostic = dict(status='failed', raw_to_reference=None, reference_to_raw=None,
        matched_features=0, fit_inliers=0, fit_inlier_ratio=None,
        validation_matches=0, validation_inliers=0, validation_inlier_ratio=None,
        fit_rmse_px=None, validation_rmse_px=None, before_rmse_px=None,
        axis_coverage=None, overlap_fraction=None)
    reasons = []
    source = reference.reshape(-1, 1, 2)
    initial = source + np.asarray(coarse, dtype=np.float32)
    options = dict(winSize=(window_px, window_px), maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 40, .001),
        flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
    dest, ok, _ = cv2.calcOpticalFlowPyrLK(view, moving_view, source, initial, **options)
    back, reverse_ok, _ = cv2.calcOpticalFlowPyrLK(moving_view, view, dest, source.copy(), **options)
    raw = dest.reshape(-1, 2)
    usable = ((ok.ravel() > 0) & (reverse_ok.ravel() > 0)
        & np.isfinite(raw).all(axis=1) & np.isfinite(back.reshape(-1, 2)).all(axis=1)
        & (np.linalg.norm(back.reshape(-1, 2)-reference, axis=1) <= config.forward_backward_px)
        & (raw[:, 0] >= 14) & (raw[:, 0] < width-14)
        & (raw[:, 1] >= 14) & (raw[:, 1] < height-14))
    ref, raw = reference[usable], raw[usable]
    diagnostic['matched_features'] = len(ref)
    # Reserve every fifth original feature before correspondence pruning:
    # these points never influence the robust fit.
    validation = np.flatnonzero(usable) % 5 == 0
    fit = ~validation
    diagnostic['validation_matches'] = int(validation.sum())
    if fit.sum() < config.min_inliers or validation.sum() < 4:
        reasons.append('insufficient_verified_matches')
    else:
        shift, inliers = fit_translation(ref[fit], raw[fit], config.inlier_radius_px)
        residual = np.linalg.norm(raw+shift-ref, axis=1)
        all_inliers = residual <= config.inlier_radius_px
        # Recheck the fit against the final transform before computing
        # statistics; empty support is a finite failed result.
        fit_support = fit & all_inliers
        inlier_count = int(fit_support.sum())
        fit_ratio = inlier_count / int(fit.sum())
        val_inliers = all_inliers & validation
        val_ratio = int(val_inliers.sum()) / int(validation.sum())
        fit_rmse = float(np.sqrt(np.mean(residual[fit_support]**2))) if fit_support.any() else None
        val_rmse = (float(np.sqrt(np.mean(residual[val_inliers]**2)))
                    if val_inliers.any() else None)
        before = (float(np.sqrt(np.mean(np.sum((raw[all_inliers]-ref[all_inliers])**2, axis=1))))
                  if all_inliers.any() else None)
        coverage = (np.ptp(ref[fit_support], axis=0) / (width, height)
                    if fit_support.any() else np.zeros(2))
        overlap = float(max(0., width-abs(shift[0])) * max(0., height-abs(shift[1])) / (width*height))
        diagnostic.update(fit_inliers=inlier_count, fit_inlier_ratio=fit_ratio,
            validation_inliers=int(val_inliers.sum()), validation_inlier_ratio=val_ratio,
            fit_rmse_px=fit_rmse, validation_rmse_px=val_rmse,
            before_rmse_px=before, axis_coverage=tuple(map(float, coverage)), overlap_fraction=overlap,
            reference_points=tuple(map(tuple, ref.astype(float))), raw_points=tuple(map(tuple, raw.astype(float))),
            inlier_flags=tuple(map(bool, all_inliers)), validation_flags=tuple(map(bool, validation)))
        if inlier_count < config.min_inliers or fit_ratio < config.min_inlier_ratio:
            reasons.append('weak_translation_consensus')
        if (int(val_inliers.sum()) < 4 or val_ratio < config.min_inlier_ratio
                or val_rmse is None or val_rmse > config.max_validation_rmse_px):
            reasons.append('validation_residual_or_support_failed')
        if min(coverage) < config.min_axis_coverage:
            reasons.append('features_not_spatially_distributed')
        if np.linalg.norm(shift) > config.max_shift_px or overlap < config.min_overlap:
            reasons.append('shift_or_overlap_exceeds_limit')
        if not reasons:
            diagnostic.update(status='estimated', raw_to_reference=_matrix(shift),
                              reference_to_raw=_matrix(-shift))
    diagnostic['warnings'] = tuple(reasons)
    return diagnostic


def register_sequence(frames: Sequence[np.ndarray], config=None) -> SequenceRegistration:
    """Fit each frame directly against frame0; a validated neighbor can seed a retry.

    1..30 equal native-size grayscale arrays; failures return diagnostics with
    null matrices. Invalid inputs raise ValueError. Reference geometry is identity,
    even if too few features make later frames fail. Inputs are never mutated.
    """
    config = RegistrationConfig.from_mapping(config)
    if (not isinstance(frames, Sequence) or isinstance(frames, (str, bytes))
            or not 1 <= len(frames) <= 30):
        raise ValueError("Expected 1..30 ordered grayscale frames")
    normalized = []
    for pixels in frames:
        if normalized and (not isinstance(pixels, np.ndarray) or pixels.shape != frames[0].shape):
            raise ValueError("Frames must share native dimensions")
        # Validation is done once; preparing/decoding is included in frame timing.
        started = perf_counter()
        normalized.append((*_prepare(pixels, config), (perf_counter()-started)*1000))
    height, width = frames[0].shape
    response, view, mask, preparation_ms = normalized[0]
    started = perf_counter()
    features = cv2.goodFeaturesToTrack(view, maxCorners=config.max_features,
        qualityLevel=.01, minDistance=config.feature_distance_px, blockSize=5, mask=mask)
    reference = np.empty((0, 2), np.float32) if features is None else features.reshape(-1, 2)
    results = [FrameRegistration(0, 'identity', _matrix((0, 0)), _matrix((0, 0)), None,
        len(reference), len(reference), len(reference), 1. if len(reference) else None,
        0, 0, None, 0., None, 0., None, 1.,
        preparation_ms+(perf_counter()-started)*1000,
        ('Insufficient reference features for cross-frame registration',)
        if len(reference) < config.min_inliers+4 else (), initialization='identity')]
    window = cv2.createHanningWindow((width, height), cv2.CV_32F)
    for index, (moving, moving_view, _, prep_ms) in enumerate(normalized[1:], 1):
        started = perf_counter()
        diagnostic = dict(frame_index=index, status='failed', raw_to_reference=None,
            reference_to_raw=None, phase_response=None, reference_features=len(reference),
            matched_features=0, fit_inliers=0, fit_inlier_ratio=None,
            validation_matches=0, validation_inliers=0, validation_inlier_ratio=None,
            fit_rmse_px=None, validation_rmse_px=None, before_rmse_px=None,
            axis_coverage=None, overlap_fraction=None, warnings=())
        reasons = []
        if len(reference) < config.min_inliers+4:
            reasons.append('insufficient_reference_features')
        else:
            # phaseCorrelate estimates reference->raw displacement; retain copies
            # because OpenCV can multiply its float inputs by the window in-place.
            coarse, phase = cv2.phaseCorrelate(response.copy(), moving.copy(), window)
            if not np.isfinite([*coarse, phase]).all():
                reasons.append('nonfinite_phase_estimate')
            else:
                diagnostic['phase_response'] = float(phase)
                if phase < config.min_phase_response:
                    reasons.append('weak_phase_correlation')
                if np.linalg.norm(coarse) > config.max_shift_px:
                    reasons.append('coarse_shift_exceeds_limit')
            if not reasons:
                diagnostic.update(_match_translation(reference, view, moving_view, coarse,
                    width, height, config))
                reasons = list(diagnostic['warnings'])
            # A phase-correlation alias can seed optical flow onto the wrong
            # streak. Use one independently validated nearby frame only to
            # initialize a fresh DIRECT frame-0 fit, never as the final transform.
            if reasons and config.neighbor_retry and index > 1:
                anchor = next((f for f in reversed(results[1:]) if f.status == 'estimated'), None)
                if anchor is not None:
                    pair = register_sequence([frames[anchor.frame_index], frames[index]],
                        {**asdict(config), 'neighbor_retry': 0}).frames[1]
                    if pair.status == 'estimated':
                        total_shift = (np.asarray(anchor.raw_to_reference)[:2, 2]
                                       + np.asarray(pair.raw_to_reference)[:2, 2])
                        if np.linalg.norm(total_shift) <= config.max_shift_px:
                            retry = _match_translation(reference, view, moving_view, -total_shift,
                                width, height, config, config.retry_flow_window_px)
                            if retry['status'] == 'estimated':
                                diagnostic.update(retry,
                                    initialization='verified_neighbor_seed_direct_fit',
                                    seed_frame_index=anchor.frame_index,
                                    flow_window_px=config.retry_flow_window_px,
                                    direct_failure_reasons=tuple(reasons))
                                reasons = []
        diagnostic.update(warnings=tuple(reasons), runtime_ms=prep_ms+(perf_counter()-started)*1000)
        results.append(FrameRegistration(**diagnostic))
    return SequenceRegistration(width, height, tuple(results), config)


def warp_to_reference(pixels, frame: FrameRegistration):
    """New float32 aligned preview plus interpolation-safe bool validity mask.

    Invalid/border pixels are zero and MUST be masked from scientific use.
    Detection should run on original images, then map its point coordinates.
    """
    image, _ = normalize_grayscale(pixels)
    if frame.status == 'failed' or frame.raw_to_reference is None:
        raise ValueError("Cannot warp a failed registration")
    matrix = np.asarray(frame.raw_to_reference, dtype=np.float64)[:2]
    size = (image.shape[1], image.shape[0])
    aligned = cv2.warpAffine(image, matrix, size, flags=cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    support = cv2.warpAffine(np.ones(image.shape, np.float32), matrix, size,
                            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    valid = support >= 1.-1.e-6
    aligned[~valid] = 0
    return aligned, valid


def add_reference_coordinates(detections, registration: SequenceRegistration):
    """Return revalidated shared Detection copies; preserve every raw field and ID.

    Reject any failed frame in the sequence, including empty frames: this tracker
    falls back to raw for null references, so partial conversion is unsafe.
    """
    from app.schemas.result import Detection
    if registration.status == 'failed':
        raise ValueError("Sequence registration failed; do not mix raw/reference frames")
    output = []
    for detection in detections:
        detection = Detection.model_validate(detection)
        if (detection.frame_index >= len(registration.frames)
                or detection.x_reference_px is not None or detection.y_reference_px is not None):
            raise ValueError("Expected in-sequence raw detections without previous registration")
        left, top, right, bottom = detection.bbox_raw_px
        if not (0 <= left < right <= registration.width_px and 0 <= top < bottom <= registration.height_px):
            raise ValueError("Detection lies outside declared native image")
        point = registration.frames[detection.frame_index].transform_points([[detection.x_raw_px, detection.y_raw_px]])[0]
        output.append(Detection.model_validate({**detection.model_dump(),
            'x_reference_px': float(point[0]), 'y_reference_px': float(point[1])}))
    return output
