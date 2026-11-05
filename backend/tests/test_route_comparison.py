"""Unit tests for route comparison computations (pure functions, no DB)."""
import pytest

from services.route_comparison import (
    bearing_difference,
    collapse_standing_points,
    compute_race_curve,
    compute_splits,
    decimate_track,
    initial_bearing,
    interpolate_time_at,
    is_direction_reversed,
    sample_track_bearing,
)


class TestCollapseStandingPoints:
    def test_keeps_first_timestamp_for_equal_distances(self):
        # Standing at 100m from t=50 to t=120: first arrival (50) survives,
        # pause seconds belong to the NEXT segment, not this one
        d, t = collapse_standing_points([0, 50, 100, 100, 100, 150], [0, 30, 50, 80, 120, 160])
        assert d == [0, 50, 100, 150]
        assert t == [0, 30, 50, 160]

    def test_no_standing_points_unchanged(self):
        d, t = collapse_standing_points([0, 10, 20], [0, 5, 10])
        assert (d, t) == ([0, 10, 20], [0, 5, 10])

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            collapse_standing_points([1, 2], [1])

    def test_empty(self):
        assert collapse_standing_points([], []) == ([], [])


class TestComputeRaceCurve:
    def test_basic_curve(self):
        curve = compute_race_curve([0, 400, 800], [0, 120, 240])
        assert curve == ([0, 400, 800], [0, 120, 240])

    def test_pauses_preserved_as_vertical_jumps(self):
        # 200m of standing (t 60->180) stays in the RAW curve: same distance,
        # advancing time = the vertical jump the race plot draws
        curve = compute_race_curve([0, 200, 200, 400], [0, 60, 180, 240])
        assert curve == ([0, 200, 200, 400], [0, 60, 180, 240])

    def test_none_for_mismatched_lengths(self):
        assert compute_race_curve([0, 1], [0]) is None

    def test_none_for_short(self):
        assert compute_race_curve([0], [0]) is None
        assert compute_race_curve([], []) is None

    def test_none_for_zero_distance(self):
        # GPS never moved — no race to plot
        assert compute_race_curve([0, 0, 0], [0, 10, 20]) is None


class TestInterpolateTimeAt:
    def test_exact_checkpoints(self):
        d, t = [0, 400, 800], [0, 100, 200]
        assert interpolate_time_at(0, d, t) == 0.0
        assert interpolate_time_at(400, d, t) == 100.0
        assert interpolate_time_at(800, d, t) == 200.0

    def test_midpoint(self):
        assert interpolate_time_at(600, [0, 400, 800], [0, 100, 200]) == 150.0

    def test_beyond_recorded_distance_returns_none(self):
        assert interpolate_time_at(900, [0, 400, 800], [0, 100, 200]) is None

    def test_before_start_returns_none(self):
        assert interpolate_time_at(-1, [0, 400], [0, 100]) is None


class TestComputeSplits:
    def test_exact_intervals(self):
        # 1:40/km pace => 400m splits of 40s
        d = [0, 400, 800, 1200]
        t = [0, 40, 80, 120]
        splits = compute_splits(d, t, 400.0)
        assert splits == [
            {"start_m": 0.0, "end_m": 400.0, "seconds": 40, "pace_s_per_km": 100},
            {"start_m": 400.0, "end_m": 800.0, "seconds": 40, "pace_s_per_km": 100},
            {"start_m": 800.0, "end_m": 1200.0, "seconds": 40, "pace_s_per_km": 100},
        ]

    def test_final_partial_segment_kept(self):
        # 1000m total, 400m checkpoints => 400, 400, 200
        splits = compute_splits([0, 250, 500, 750, 1000], [0, 25, 50, 75, 100], 400.0)
        assert [s["end_m"] for s in splits] == [400.0, 800.0, 1000.0]
        assert splits[-1]["seconds"] == 20

    def test_pauses_attributed_to_following_segment(self):
        # 400m run (100s), then 60s standing, then 400m run. With first-
        # arrival collapse, time-at-400m = 100 => the pause belongs to the
        # SECOND segment (100s moving + 60s paused = 160s)
        curve_d, curve_t = [0, 400, 400, 800], [0, 100, 160, 260]
        splits = compute_splits(curve_d, curve_t, 400.0)
        assert splits[0]["seconds"] == 100
        assert splits[1]["seconds"] == 160  # 100s moving + 60s pause
        assert splits[1]["pace_s_per_km"] == 400  # 160s / 0.4km

    def test_activity_shorter_than_one_checkpoint(self):
        splits = compute_splits([0, 300], [0, 90], 400.0)
        assert splits == [{"start_m": 0.0, "end_m": 300.0, "seconds": 90, "pace_s_per_km": 300}]

    def test_none_for_unusable_streams(self):
        assert compute_splits([0, 0, 0], [0, 1, 2], 400.0) is None


class TestBearings:
    def test_cardinal_directions(self):
        # Great-circle initial bearings, not rhumb lines: east at 40°N starts
        # at 89.97°, not exactly 90 — hence the 0.1° tolerance
        assert initial_bearing(40.0, -74.0, 40.1, -74.0) == pytest.approx(0.0, abs=0.1)
        assert initial_bearing(40.0, -74.0, 40.0, -73.9) == pytest.approx(90.0, abs=0.1)
        assert initial_bearing(40.0, -74.0, 39.9, -74.0) == pytest.approx(180.0, abs=0.1)
        assert initial_bearing(40.0, -74.0, 40.0, -74.1) == pytest.approx(270.0, abs=0.1)

    def test_bearing_difference_wraps_at_360(self):
        assert bearing_difference(359.0, 1.0) == pytest.approx(2.0)
        assert bearing_difference(10.0, 350.0) == pytest.approx(20.0)
        assert bearing_difference(0.0, 180.0) == pytest.approx(180.0)

    def test_sample_track_bearing_straight_line(self):
        # 200m of eastward points
        track = [[40.0, -74.0 + i * 0.00025] for i in range(10)]  # ~27m/pt
        assert sample_track_bearing(track) == pytest.approx(90.0, abs=1.0)

    def test_sample_track_bearing_none_for_stationary(self):
        # All points identical: never 150m from start
        assert sample_track_bearing([[40.0, -74.0]] * 10) is None

    def test_sample_track_bearing_none_for_single_point(self):
        assert sample_track_bearing([[40.0, -74.0]]) is None


class TestDirectionReversed:
    # Route runs north (start -> end = +lat)
    ROUTE_START = (40.0, -74.0)
    ROUTE_END = (40.1, -74.0)

    def test_forward_run_not_reversed(self):
        track = [[40.0 + i * 0.0005, -74.0] for i in range(10)]  # heading north
        assert is_direction_reversed(track, self.ROUTE_START, self.ROUTE_END) is False

    def test_reverse_run_detected(self):
        track = [[40.1 - i * 0.0005, -74.0] for i in range(10)]  # heading south
        assert is_direction_reversed(track, self.ROUTE_START, self.ROUTE_END) is True

    def test_undeterminable_track_counts_as_forward(self):
        # Stationary jitter: no 150m sample => can't tell => False (still no splits via plot None)
        track = [[40.0 + (i % 3) * 1e-6, -74.0 + (i % 2) * 1e-6] for i in range(12)]
        assert is_direction_reversed(track, self.ROUTE_START, self.ROUTE_END) is False


class TestDecimateTrack:
    def test_short_track_unchanged(self):
        track = [[40.0, -74.0], [40.001, -74.0]]
        assert decimate_track(track) is track

    def test_decimates_to_max_points(self):
        track = [[40.0 + i * 1e-5, -74.0] for i in range(2000)]
        out = decimate_track(track, max_points=500)
        assert len(out) == 500
        assert out[0] == track[0]
        assert out[-1] == track[-1]