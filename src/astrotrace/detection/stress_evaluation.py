"""Post-inference synthetic association diagnostics, not official MOT scoring.

Never imported by detector, registration or tracking. Raw point matching uses the
existing maximum-cardinality inclusive gate. Predictions are excluded entirely.
Identity metrics exclude geometrically coincident truths (<=1 px apart).
"""

from collections import Counter, defaultdict

import numpy as np

from .evaluation import match_points, summarize_frames


def evaluate_stress(detections, tracks, truth: dict, *, radius_px: float = 5.) -> dict:
    """Report detection counts and identity continuity using separate render truth.

    Switch: a truth's next matched observation has a different predicted track ID.
    Fragmentation: number of distinct matched tracks per truth minus one.
    Correct link: consecutive identity-resolvable matches within one predicted
    track share a truth ID. False confirmed: confirmed track with fewer than three
    matches to any one truth. Gap recovery requires matches on both sides and
    same track ID; missing endpoint matches are reported as unscorable, not success.
    """
    matches, frame_results, ambiguous, visible_by_frame = {}, [], set(), {}
    for frame in truth['frames']:
        index = frame['frame_index']
        targets = [obj for obj in frame['objects'] if obj['visible']]
        visible_by_frame[index] = {obj['object_id'] for obj in targets}
        predictions = [d for d in detections if d.frame_index == index]
        points = [obj['raw_xy_px'] for obj in targets]
        scored = match_points([(d.x_raw_px, d.y_raw_px) for d in predictions], points, radius_px)
        frame_results.append({'frame_index': index, **scored})
        if points:
            distances = np.linalg.norm(np.asarray(points)[:, None] - np.asarray(points)[None, :], axis=2)
            np.fill_diagonal(distances, np.inf)
            ambiguous.update((index, targets[i]['object_id']) for i in range(len(points)) if distances[i].min() <= 1.)
        for match in scored['matches']:
            detection = predictions[match['predicted_index']]
            matches[detection.detection_id] = (index, targets[match['truth_index']]['object_id'])
    by_truth = defaultdict(list)
    correct = wrong = false_confirmed = unscorable_confirmed = 0
    seen = set()
    for track in tracks:
        labels = []
        support = Counter()
        has_ambiguous = False
        for point in track.points:
            if point.point_type != 'observed':
                continue
            if point.detection_id in seen:
                raise ValueError('Detection assigned to more than one observed point')
            seen.add(point.detection_id)
            matched = matches.get(point.detection_id)
            if matched in ambiguous:
                has_ambiguous = True
                continue
            if matched is None:
                continue
            index, object_id = matched
            labels.append((index, object_id))
            support[object_id] += 1
            by_truth[object_id].append((index, track.track_id))
        labels.sort()
        for a, b in zip(labels, labels[1:]):
            if a[1] == b[1]:
                correct += 1
            else:
                wrong += 1
        # Include tracks confirmed earlier and subsequently ended. This snapshot
        # uses three actual observations to confirm; never include predictions.
        if track.observed_count >= 3:
            if has_ambiguous:
                unscorable_confirmed += 1
            elif max(support.values(), default=0) < 3:
                false_confirmed += 1
    if seen != {d.detection_id for d in detections}:
        raise ValueError('Tracker observations must consume exactly the actual detections')
    switches = fragmentation = recovered = failed_gaps = unscorable = 0
    for observations in by_truth.values():
        observations.sort()
        switches += sum(a[1] != b[1] for a, b in zip(observations, observations[1:]))
        fragmentation += max(0, len({track for _, track in observations})-1)
    ids = {obj['object_id'] for frame in truth['frames'] for obj in frame['objects']}
    for object_id in ids:
        # Scripted missing renders bounded by visible endpoints only.
        visible = [f['frame_index'] for f in truth['frames'] if object_id in visible_by_frame[f['frame_index']]]
        observed = dict(by_truth[object_id])
        for before, after in zip(visible, visible[1:]):
            if after-before not in (2, 3):
                continue
            hidden = [obj for frame in truth['frames'] if before < frame['frame_index'] < after
                      for obj in frame['objects'] if obj['object_id'] == object_id]
            if not hidden or any(obj['reason'] != 'simulated_miss' for obj in hidden):
                continue
            if before not in observed or after not in observed:
                unscorable += 1
            elif observed[before] == observed[after]:
                recovered += 1
            else:
                failed_gaps += 1
    return {'matching_radius_px': radius_px, 'identity_ambiguity_radius_px': 1.,
            'detection': summarize_frames(frame_results, []), 'per_frame': frame_results,
            'association': {'correct_links': correct, 'incorrect_links': wrong,
                'correct_link_fraction': correct/(correct+wrong) if correct+wrong else None,
                'identity_switches': switches, 'fragmentation': fragmentation,
                'scripted_gaps_recovered': recovered, 'scripted_gaps_failed': failed_gaps,
                'scripted_gaps_unscorable': unscorable, 'false_confirmed_tracks': false_confirmed,
                'false_confirmation_unscorable_tracks': unscorable_confirmed,
                'ambiguous_truth_observations_excluded': len(ambiguous),
                'tracks': len(tracks), 'confirmed_tracks': sum(t.status == 'confirmed' for t in tracks)},
            'predicted_points_scored': False, 'scope': 'authored synthetic diagnostic; not IDF1/HOTA or debris classification'}
