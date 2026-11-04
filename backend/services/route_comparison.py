"""
Route comparison computations — pure functions, no DB access.

Consumes aligned per-point (time, distance) streams persisted at upload
(time = relative seconds from activity start, distance = cumulative meters
from GPS) and produces:

- race plot curves: cumulative elapsed time vs cumulative distance, with
  pauses rendered as vertical jumps (time advances, distance doesn't)
- splits: elapsed time per fixed-distance checkpoint segment, via linear
  interpolation of the (distance, time) curve
- initial-bearing direction detection: did this activity run the route
  backwards relative to the route's canonical start->end direction?
- track decimation for map overlays

All functions tolerate GPS noise: distance is monotone non-decreasing by
construction (segment distances are always positive), but consecutive
equal distances (standing still) are collapsed before interpolation,
keeping the LAST timestamp so pauses appear as time jumps.
"""

from math import atan2, radians, sin, cos, sqrt, asin, degrees
from bisect import bisect_right
from typing import List, Optional, Tuple

# A route shorter than this can't have a meaningful initial bearing sample
MIN_BEARING_SAMPLE_M = 150.0
# Bearing difference beyond this is considered "ran the other way"
REVERSED_BEARING_THRESHOLD_DEG = 90.0


def collapse_standing_points(
    distances: List[float], times: List[int]
) -> Tuple[List[float], List[int]]:
    """Collapse consecutive points at the same cumulative distance.

    Used for TIME INTERPOLATION ONLY (split checkpoints need strictly
    increasing distances). Keeping the FIRST timestamp means "time at
    distance d" = first arrival — a pause then belongs to the segment
    AFTER the pause point, not smeared into the split that just ended.

    The race plot does NOT use this: it needs the raw curve so pauses
    render as vertical jumps (same distance, advancing time).
    """
    if len(distances) != len(times):
        raise ValueError("distance and time streams must be equal length")
    if not distances:
        return [], []

    out_d: List[float] = [distances[0]]
    out_t: List[int] = [times[0]]
    for d, t in zip(distances[1:], times[1:]):
        if d == out_d[-1]:
            continue  # standing: first arrival already recorded
        out_d.append(d)
        out_t.append(t)
    return out_d, out_t


def compute_race_curve(
    distances: List[float], times: List[int]
) -> Optional[Tuple[List[float], List[int]]]:
    """Race plot curve: (distances, elapsed_seconds), both cumulative, RAW.

    Pauses deliberately stay in as consecutive pairs sharing a distance
    with different times — they render as vertical jumps (time advances,
    distance doesn't), showing the break exactly where it happened.
    Returns None when the streams are unusable (missing/short/mismatched).
    """
    if not distances or not times or len(distances) != len(times):
        return None
    if len(distances) < 2:
        return None
    if distances[-1] <= 0:
        return None
    return distances, times


def interpolate_time_at(
    checkpoint_m: float, distances: List[float], times: List[int]
) -> Optional[float]:
    """Linear interpolation of elapsed time at a cumulative distance.

    Assumes `distances` is strictly increasing (call collapse first).
    Returns None when the checkpoint lies beyond the recorded distance.
    """
    if checkpoint_m < distances[0] or checkpoint_m > distances[-1]:
        return None
    if checkpoint_m == distances[0]:
        return float(times[0])
    if checkpoint_m == distances[-1]:
        return float(times[-1])
    idx = bisect_right(distances, checkpoint_m)
    d0, d1 = distances[idx - 1], distances[idx]
    t0, t1 = times[idx - 1], times[idx]
    if d1 == d0:  # defensive; collapse makes this unreachable
        return float(t1)
    frac = (checkpoint_m - d0) / (d1 - d0)
    return t0 + (t1 - t0) * frac


def compute_splits(
    distances: List[float],
    times: List[int],
    checkpoint_interval_m: float = 400.0,
) -> Optional[List[dict]]:
    """Split times per checkpoint_interval_m segment.

    Checkpoints sit at interval, 2*interval, ... up to the final recorded
    distance; the last segment runs from the last full checkpoint to the
    actual finish (partial segments are real running, they stay in).
    Standing-still points are collapsed (first-arrival times) so pause
    seconds land in the segment AFTER the pause point.
    Returns None when the streams are unusable.
    """
    curve = compute_race_curve(distances, times)
    if curve is None:
        return None
    d, t = collapse_standing_points(*curve)

    splits: List[dict] = []
    start_m = 0.0
    start_t = float(t[0])
    checkpoint = checkpoint_interval_m
    while checkpoint < d[-1]:
        end_t = interpolate_time_at(checkpoint, d, t)
        if end_t is not None:
            splits.append(_split(start_m, checkpoint, start_t, end_t))
            start_m, start_t = checkpoint, end_t
        checkpoint += checkpoint_interval_m
    # Final segment: last checkpoint (or start) to the actual finish
    if d[-1] - start_m > 0:
        splits.append(_split(start_m, d[-1], start_t, float(t[-1])))
    return splits


def _split(start_m: float, end_m: float, start_t: float, end_t: float) -> dict:
    seconds = end_t - start_t
    segment_km = (end_m - start_m) / 1000.0
    pace = seconds / segment_km if segment_km > 0.001 else None
    return {
        "start_m": round(start_m, 1),
        "end_m": round(end_m, 1),
        "seconds": round(seconds),
        "pace_s_per_km": round(pace) if pace is not None else None,
    }


def initial_bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Initial bearing (degrees, 0=north, clockwise) from point 1 to point 2."""
    lat1r, lat2r = radians(lat1), radians(lat2)
    dlng = radians(lng2 - lng1)
    x = sin(dlng) * cos(lat2r)
    y = cos(lat1r) * sin(lat2r) - sin(lat1r) * cos(lat2r) * cos(dlng)
    return (degrees(atan2(x, y)) + 360.0) % 360.0


def _normalize_bearing(deg: float) -> float:
    return (deg + 360.0) % 360.0


def bearing_difference(a: float, b: float) -> float:
    """Absolute smallest difference between two bearings, in degrees [0, 180]."""
    diff = abs(_normalize_bearing(a) - _normalize_bearing(b))
    return diff if diff <= 180.0 else 360.0 - diff


def sample_track_bearing(latlng: List[List[float]]) -> Optional[float]:
    """Initial bearing of a track: start point to the first point at least
    MIN_BEARING_SAMPLE_M away (haversine). None when the track is too short
    to have a direction (loops back on itself immediately, single point...)."""

    if len(latlng) < 2:
        return None
    lat0, lng0 = latlng[0]
    for lat, lng in latlng[1:]:
        if _haversine_m(lat0, lng0, lat, lng) >= MIN_BEARING_SAMPLE_M:
            return initial_bearing(lat0, lng0, lat, lng)
    return None


def is_direction_reversed(
    activity_latlng: List[List[float]],
    route_start: Tuple[float, float],
    route_end: Tuple[float, float],
) -> bool:
    """True when the activity plausibly ran the route backwards.

    Compares the activity's initial bearing against the route's
    start->end bearing. Undeterminable tracks (too short to sample)
    count as NOT reversed — they can't produce splits anyway.
    """
    track_bearing = sample_track_bearing(activity_latlng)
    if track_bearing is None:
        return False
    route_bearing = initial_bearing(route_start[0], route_start[1], route_end[0], route_end[1])
    return bearing_difference(track_bearing, route_bearing) > REVERSED_BEARING_THRESHOLD_DEG


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371000.0
    lat1r, lat2r = radians(lat1), radians(lat2)
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(lat1r) * cos(lat2r) * sin(dlng / 2) ** 2
    return 2 * R * asin(sqrt(a))


def decimate_track(latlng: List[List[float]], max_points: int = 500) -> List[List[float]]:
    """Even-stride decimation for map overlays. Always keeps first+last."""
    if len(latlng) <= max_points:
        return latlng
    stride = len(latlng) / max_points
    kept = [latlng[int(i * stride)] for i in range(max_points)]
    if kept[-1] != latlng[-1]:
        kept[-1] = latlng[-1]
    return kept