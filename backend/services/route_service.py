"""
Route building service.

Derives Route rows from an activity's stored latlng stream so the Routes
page shows one row per real-world route with a count of matching
activities.

Matching is two-tier:

  1. EXACT  — SHA-256 of the canonicalized, encoded polyline. Catches
     re-uploads of the same file and rare bit-identical recordings.
  2. FUZZY  — for everything else: compare the canonical path against
     existing routes whose start point is within ~300m, using symmetric
     mean nearest-point distance. Under ~50m → same route.

Why exact-only wasn't enough (measured): GPS recordings of the same loop
differ by a few meters per point. After Douglas-Peucker simplification
the surviving vertices are far apart, so each keeps its own few-meter
offset, and no reasonable rounding grid absorbs it reliably — per-vertex
boundary flips compound across the whole path, so most re-runs hash
differently. Hash-matching alone would fill the Routes page with
near-duplicates, hence the fuzzy tier.

Canonicalization pipeline (deterministic across devices/runs):
  1. Drop consecutive duplicate points (GPS hold at low speed)
  2. Douglas-Peucker simplify to ~5m tolerance (kills jitter noise)
  3. Encode with the Google/Mapbox polyline algorithm (precision 5)

Known limitations (documented, accepted for this PR):
  - A route run in reverse hashes/compares differently → separate row.
  - A detour on one recording raises the mean distance → separate row.
    If near-duplicates get annoying, raise the threshold or add
    sequence-aware matching later.

Rollup semantics (per design decision in the PR discussion):
  - activity_count is the source of truth and always increments.
  - distance/elevation are refreshed as rolling averages across all
    matching recordings, so GPS-quality noise converges instead of
    sticking with whatever recorded first.
"""
import hashlib
import math
from typing import Dict, List, Optional, Sequence, Tuple

import polyline as polyline_codec
from sqlalchemy.orm import Session

from models.activity import Activity
from models.activity_stream import ActivityStream
from models.route import Route

# Douglas-Peucker tolerance in meters. 5m keeps the shape visually
# identical on the map while killing GPS noise.
SIMPLIFY_TOLERANCE_M = 5.0

# Encoded polyline precision (5 = standard Google/Mapbox precision).
POLYLINE_PRECISION = 5

# Routes shorter than this aren't interesting as "routes" (GPS drift
# around a stationary point, treadmill-ish tracks, bad uploads).
MIN_ROUTE_POINTS = 10
MIN_ROUTE_DISTANCE_M = 200.0

# Fuzzy matching
FUZZY_CANDIDATE_START_M = 300.0  # candidate routes must start within this
FUZZY_MATCH_THRESHOLD_M = 50.0   # symmetric mean distance below this = same route
FUZZY_SAMPLE_COUNT = 32          # resample both paths to N points for comparison


def haversine_m(a: Sequence[float], b: Sequence[float]) -> float:
    """Great-circle distance in meters between two (lat, lng) points."""
    lat1, lng1, lat2, lng2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    )
    return 2 * 6371000.0 * math.asin(math.sqrt(h))


def path_length_m(coords: Sequence[Sequence[float]]) -> float:
    """Total length in meters of a coordinate path."""
    return sum(
        haversine_m(coords[i], coords[i + 1])
        for i in range(len(coords) - 1)
    )


def _perpendicular_distance_m(
    point: Sequence[float], start: Sequence[float], end: Sequence[float]
) -> float:
    """
    Distance from `point` to the segment start→end.

    Uses an equirectangular projection around the segment midpoint —
    plenty accurate for a 5m tolerance at running/riding distances and
    avoids pulling in a geometry dependency.
    """
    lat0 = math.radians((start[0] + end[0]) / 2)

    def to_xy(p: Sequence[float]) -> Tuple[float, float]:
        return (
            math.radians(p[1]) * math.cos(lat0) * 6371000.0,
            math.radians(p[0]) * 6371000.0,
        )

    px, py = to_xy(point)
    ax, ay = to_xy(start)
    bx, by = to_xy(end)
    dx, dy = bx - ax, by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def douglas_peucker(
    coords: Sequence[Sequence[float]], tolerance_m: float = SIMPLIFY_TOLERANCE_M
) -> List[Sequence[float]]:
    """Douglas-Peucker simplification with a metric tolerance."""
    if len(coords) <= 2:
        return list(coords)

    def simplify(points: List[Sequence[float]]) -> List[Sequence[float]]:
        if len(points) <= 2:
            return points
        start, end = points[0], points[-1]
        max_dist, max_idx = 0.0, 0
        for i in range(1, len(points) - 1):
            d = _perpendicular_distance_m(points[i], start, end)
            if d > max_dist:
                max_dist, max_idx = d, i
        if max_dist > tolerance_m:
            left = simplify(points[: max_idx + 1])
            right = simplify(points[max_idx:])
            return left[:-1] + right
        return [start, end]

    return simplify(list(coords))


def canonicalize(latlng: Sequence[Sequence[float]]) -> List[Sequence[float]]:
    """
    Canonical coordinate path for encoding/matching: drop consecutive
    duplicates, then Douglas-Peucker simplify. Returns [] when the track
    is too short to be a route.
    """
    deduped: List[Sequence[float]] = []
    for pt in latlng:
        if not pt or len(pt) < 2:
            continue
        if deduped and pt[0] == deduped[-1][0] and pt[1] == deduped[-1][1]:
            continue
        deduped.append(pt)

    if len(deduped) < MIN_ROUTE_POINTS:
        return []

    simplified = douglas_peucker(deduped, SIMPLIFY_TOLERANCE_M)

    if path_length_m(simplified) < MIN_ROUTE_DISTANCE_M:
        return []

    return simplified


def resample_uniform(
    coords: Sequence[Sequence[float]], count: int = FUZZY_SAMPLE_COUNT
) -> List[Tuple[float, float]]:
    """
    Resample a path to N points at even fractions of total path length.
    Makes comparison independent of where GPS happened to record points.
    """
    if not coords:
        return []
    pts = [(float(c[0]), float(c[1])) for c in coords]
    if len(pts) == 1:
        return [pts[0]]

    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + haversine_m(pts[i - 1], pts[i]))
    total = cum[-1]
    if total == 0:
        return [pts[0]]

    samples: List[Tuple[float, float]] = []
    seg = 0
    for k in range(count):
        target = total * k / (count - 1)
        while seg < len(cum) - 2 and cum[seg + 1] < target:
            seg += 1
        span = cum[seg + 1] - cum[seg]
        t = 0.0 if span == 0 else (target - cum[seg]) / span
        t = max(0.0, min(1.0, t))
        lat = pts[seg][0] + (pts[seg + 1][0] - pts[seg][0]) * t
        lng = pts[seg][1] + (pts[seg + 1][1] - pts[seg][1]) * t
        samples.append((lat, lng))
    return samples


def symmetric_path_distance_m(
    path_a: Sequence[Sequence[float]], path_b: Sequence[Sequence[float]]
) -> float:
    """
    Mean symmetric distance between two paths: for each resampled point on
    A, distance to the nearest point on B, and vice versa. Returns inf
    for empty paths. Crude but stable for "same shape?" at 50m thresholds.
    """
    if not path_a or not path_b:
        return float("inf")

    a = resample_uniform(path_a)
    b = resample_uniform(path_b)

    def mean_min_dist(src: List[Tuple[float, float]], dst: List[Tuple[float, float]]) -> float:
        total = 0.0
        for p in src:
            total += min(haversine_m(p, q) for q in dst)
        return total / len(src)

    return (mean_min_dist(a, b) + mean_min_dist(b, a)) / 2.0


def _encoded_polyline(coords: Sequence[Sequence[float]]) -> str:
    return polyline_codec.encode(
        [(float(c[0]), float(c[1])) for c in coords], precision=POLYLINE_PRECISION
    )


def polyline_hash_for(
    latlng: Sequence[Sequence[float]],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (encoded_polyline, sha256_hash) for the canonicalized track,
    or (None, None) when the track is too short to be a route.
    """
    canonical = canonicalize(latlng)
    if not canonical:
        return (None, None)
    encoded = _encoded_polyline(canonical)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return (encoded, digest)


def _activity_elevation_m(activity: Activity) -> Optional[float]:
    elev = getattr(activity, "total_elevation_gain", None)
    return float(elev) if elev is not None else None


def _activity_distance_m(activity: Activity) -> Optional[float]:
    dist = getattr(activity, "distance", None)
    return float(dist) if dist is not None else None


def find_or_create_route(
    db: Session, activity: Activity, latlng: Sequence[Sequence[float]]
) -> Optional[Route]:
    """
    Find the Route matching this activity's GPS track, or create one.

    New track → insert row (name from activity, distance/elevation from
    the recording), link activity, count = 1.
    Known route (exact or fuzzy) → rolling-average refresh of
    distance/elevation (measurements converge on the true values; counts
    stay exact), bump activity_count, link the activity.

    Caller is responsible for commit.
    """
    canonical = canonicalize(latlng)
    if not canonical:
        return None

    encoded = _encoded_polyline(canonical)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    # Tier 1: exact hash match
    route = db.query(Route).filter(Route.polyline_hash == digest).first()

    # Tier 2: fuzzy match against near-start candidates
    if route is None:
        route = _find_fuzzy_match(db, canonical)

    if route is not None:
        _rollup_match(route, activity, canonical)
        return route

    # New route: seed metadata from this recording
    route = Route(
        name=getattr(activity, "name", None) or f"Route {getattr(activity, 'id', '?')}",
        polyline=encoded,
        polyline_hash=digest,
        distance=_activity_distance_m(activity) or path_length_m(canonical),
        elevation_gain=_activity_elevation_m(activity),
        start_lat=canonical[0][0],
        start_lng=canonical[0][1],
        end_lat=canonical[-1][0],
        end_lng=canonical[-1][1],
        activity_count=0,
    )
    db.add(route)
    db.flush()  # assign route.id before the count rollup below
    route.activity_count = 1
    activity.route_id = route.id
    return route


def _find_fuzzy_match(
    db: Session, canonical: Sequence[Sequence[float]]
) -> Optional[Route]:
    """
    Nearest-start candidate whose resampled path is within the fuzzy
    threshold. Bounding-box prefilter keeps the comparison set tiny
    (only routes starting within ~300m of this track's start).
    """
    start = canonical[0]
    lat_pad = FUZZY_CANDIDATE_START_M / 111_000.0
    lng_scale = 111_000.0 * max(0.1, math.cos(math.radians(start[0])))
    lng_pad = FUZZY_CANDIDATE_START_M / lng_scale

    candidates = (
        db.query(Route)
        .filter(
            Route.start_lat >= start[0] - lat_pad,
            Route.start_lat <= start[0] + lat_pad,
            Route.start_lng >= start[1] - lng_pad,
            Route.start_lng <= start[1] + lng_pad,
        )
        .all()
    )
    if not candidates:
        return None

    best_route: Optional[Route] = None
    best_dist = float("inf")
    for candidate in candidates:
        if not candidate.polyline:
            continue
        try:
            other = polyline_codec.decode(
                candidate.polyline, precision=POLYLINE_PRECISION
            )
        except ValueError:
            continue
        mean_d = symmetric_path_distance_m(canonical, other)
        if mean_d < best_dist:
            best_dist = mean_d
            best_route = candidate

    if best_route is not None and best_dist < FUZZY_MATCH_THRESHOLD_M:
        return best_route
    return None


def _rollup_match(
    route: Route, activity: Activity, canonical: Sequence[Sequence[float]]
) -> None:
    """
    A recording matched an existing route: bump the count and refresh
    distance/elevation as rolling averages so noisy single recordings
    converge on the true route measurements.
    """
    n = route.activity_count or 0
    new_count = n + 1

    track_len = path_length_m(canonical)
    if track_len > 0:
        # NUMERIC columns come back as Decimal — coerce before the math
        current_dist = float(route.distance) if route.distance is not None else None
        route.distance = (
            (current_dist * n + track_len) / new_count
            if current_dist is not None
            else track_len
        )

    elev = _activity_elevation_m(activity)
    if elev is not None:
        current_elev = float(route.elevation_gain) if route.elevation_gain is not None else None
        route.elevation_gain = (
            (current_elev * n + elev) / new_count
            if current_elev is not None
            else elev
        )

    route.activity_count = new_count
    activity.route_id = route.id


def build_route_for_activity(db: Session, activity: Activity) -> Optional[Route]:
    """
    High-level entry: look up the activity's latlng stream and attach a
    route. Caller is responsible for commit.

    Returns the route, or None when there's no usable GPS track.
    """
    stream = (
        db.query(ActivityStream)
        .filter(
            ActivityStream.activity_id == activity.id,
            ActivityStream.stream_type == "latlng",
        )
        .first()
    )
    if not stream or not stream.data:
        return None

    return find_or_create_route(db, activity, stream.data)


def backfill_routes(db: Session) -> Dict[str, int]:
    """
    Build routes for every activity that has a latlng stream. Idempotent:
    activities already linked to a matching route are counted as matched
    but do not double-count (see find_or_create_route semantics below —
    a re-run re-matches the same route and bumps counts, so backfill
    tracks which activities it already processed via the route link).

    Returns counters for logging/verification.
    """
    stats: Dict[str, int] = {
        "activities_scanned": 0,
        "routes_created": 0,
        "routes_matched": 0,
        "skipped": 0,
    }

    stream_rows = (
        db.query(ActivityStream.activity_id, ActivityStream.data)
        .filter(ActivityStream.stream_type == "latlng")
        .all()
    )
    activity_ids = [row[0] for row in stream_rows]

    routes_before = db.query(Route).count()

    for activity_id in activity_ids:
        stats["activities_scanned"] += 1
        activity = db.query(Activity).filter(Activity.id == activity_id).first()
        if not activity:
            stats["skipped"] += 1
            continue

        # Idempotence: an activity already linked to a route is skipped so
        # re-running the backfill doesn't double activity_count values.
        if activity.route_id is not None:
            stats["routes_matched"] += 1
            continue

        route = build_route_for_activity(db, activity)
        if route is None:
            stats["skipped"] += 1
        else:
            # Distinguish created vs matched by re-counting after commit
            routes_now = db.query(Route).count()
            if routes_now > routes_before:
                stats["routes_created"] += 1
                routes_before = routes_now
            else:
                stats["routes_matched"] += 1
        db.commit()

    return stats
