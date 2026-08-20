"""
Tests for analytics engine - trend calculations and aggregations
"""
import pytest
from datetime import datetime, timedelta
from services.analytics_engine import AnalyticsEngine


class TestAnalyticsEngineCalculations:
    """Test pure calculation methods (no DB needed)"""
    
    def test_compute_hr_pace_ratio(self):
        """Test HR/pace ratio calculation"""
        # Normal case: 150 bpm / 3.0 m/s = 50
        ratio = AnalyticsEngine.compute_hr_pace_ratio(150.0, 3.0)
        assert ratio == 50.0
        
        # Edge case: zero pace
        ratio = AnalyticsEngine.compute_hr_pace_ratio(150.0, 0.0)
        assert ratio == 0.0
    
    def test_compute_grade_adjusted_pace(self):
        """Test grade-adjusted pace calculation"""
        # Flat run: 5:00/km (300 s/km) with no elevation
        pace = 300.0  # seconds per km
        adjusted = AnalyticsEngine.compute_grade_adjusted_pace(pace, 0.0, 1000.0)
        assert adjusted == pace
        
        # Hilly run: 5% grade should add adjustment
        adjusted = AnalyticsEngine.compute_grade_adjusted_pace(pace, 50.0, 1000.0)
        assert adjusted > pace
        
        # Edge case: zero distance
        adjusted = AnalyticsEngine.compute_grade_adjusted_pace(pace, 50.0, 0.0)
        assert adjusted == pace
    
    def test_compute_running_economy(self):
        """Test running economy calculation"""
        # Normal case
        economy = AnalyticsEngine.compute_running_economy(150.0, 3.0, 70.0)
        expected = 150.0 / (3.0 * 70.0)
        assert abs(economy - expected) < 0.001
        
        # Edge case: zero pace
        economy = AnalyticsEngine.compute_running_economy(150.0, 0.0, 70.0)
        assert economy == 0.0
        
        # Edge case: zero weight
        economy = AnalyticsEngine.compute_running_economy(150.0, 3.0, 0.0)
        assert economy == 0.0
    
    def test_compute_heart_rate_drift(self):
        """Test heart rate drift calculation"""
        # Positive drift (HR increases over time)
        drift = AnalyticsEngine.compute_heart_rate_drift(140.0, 155.0)
        assert drift == 15.0
        
        # Negative drift (HR decreases - unusual but possible)
        drift = AnalyticsEngine.compute_heart_rate_drift(155.0, 140.0)
        assert drift == -15.0
        
        # Zero drift
        drift = AnalyticsEngine.compute_heart_rate_drift(150.0, 150.0)
        assert drift == 0.0


class TestTrendCalculation:
    """Test linear regression trend calculation"""
    
    def test_calculate_trend_insufficient_data(self):
        """Test trend with less than 2 data points"""
        # Empty
        result = AnalyticsEngine.calculate_trend([], [])
        assert result["slope"] == 0
        assert result["direction"] == "stable"
        assert result["r_squared"] == 0
        
        # Single point
        result = AnalyticsEngine.calculate_trend(
            [datetime(2024, 1, 1)],
            [10.0]
        )
        assert result["slope"] == 0
        assert result["direction"] == "stable"
    
    def test_calculate_trend_increasing(self):
        """Test trend detection for increasing values"""
        # 10 days, values increase from 10 to 20
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(10)]
        values = [10.0 + i for i in range(10)]
        
        result = AnalyticsEngine.calculate_trend(dates, values)
        
        assert result["slope"] > 0
        assert result["direction"] == "increasing"
        assert result["r_squared"] > 0.9  # Strong linear relationship
        assert "intercept" in result
        assert "p_value" in result
    
    def test_calculate_trend_decreasing(self):
        """Test trend detection for decreasing values"""
        # 10 days, values decrease from 20 to 10
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(10)]
        values = [20.0 - i for i in range(10)]
        
        result = AnalyticsEngine.calculate_trend(dates, values)
        
        assert result["slope"] < 0
        assert result["direction"] == "decreasing"
        assert result["r_squared"] > 0.9
    
    def test_calculate_trend_stable(self):
        """Test trend detection for stable values"""
        # 10 days, values stay around 15
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(10)]
        values = [15.0] * 10
        
        result = AnalyticsEngine.calculate_trend(dates, values)
        
        assert abs(result["slope"]) < 0.01
        assert result["direction"] == "stable"
        # R² should be 0 or very low for constant values
        assert result["r_squared"] < 0.1
    
    def test_calculate_trend_noisy_data(self):
        """Test trend with noisy but generally increasing data"""
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(20)]
        # Generally increasing but with noise
        values = [10.0 + i * 0.5 + (i % 3) * 0.5 for i in range(20)]
        
        result = AnalyticsEngine.calculate_trend(dates, values)
        
        assert result["slope"] > 0
        assert result["direction"] == "increasing"
        # R² should be moderate due to noise
        assert 0.5 < result["r_squared"] < 1.0


class TestAggregation:
    """Test time-based aggregation"""
    
    def test_aggregate_by_period_empty(self):
        """Test aggregation with empty data"""
        result = AnalyticsEngine.aggregate_by_period([], [], "weekly")
        assert result == []
    
    def test_aggregate_by_period_daily(self):
        """Test daily aggregation"""
        # 3 days with multiple activities per day
        dates = [
            datetime(2024, 1, 1, 8, 0),
            datetime(2024, 1, 1, 18, 0),
            datetime(2024, 1, 2, 9, 0),
            datetime(2024, 1, 3, 7, 0),
            datetime(2024, 1, 3, 12, 0),
            datetime(2024, 1, 3, 19, 0),
        ]
        values = [10.0, 12.0, 15.0, 8.0, 9.0, 11.0]
        
        result = AnalyticsEngine.aggregate_by_period(dates, values, "daily")
        
        assert len(result) == 3  # 3 days
        
        # Day 1: mean of 10, 12 = 11
        day1 = next(r for r in result if r["period"] == "2024-01-01")
        assert day1["value"] == 11.0
        assert day1["min"] == 10.0
        assert day1["max"] == 12.0
        assert day1["count"] == 2
        
        # Day 2: single value
        day2 = next(r for r in result if r["period"] == "2024-01-02")
        assert day2["value"] == 15.0
        assert day2["count"] == 1
        
        # Day 3: mean of 8, 9, 11 = 9.33
        day3 = next(r for r in result if r["period"] == "2024-01-03")
        assert abs(day3["value"] - 9.333) < 0.01
        assert day3["min"] == 8.0
        assert day3["max"] == 11.0
        assert day3["count"] == 3
    
    def test_aggregate_by_period_weekly(self):
        """Test weekly aggregation"""
        # 2 weeks of data
        dates = [
            datetime(2024, 1, 1),  # Week 1
            datetime(2024, 1, 3),
            datetime(2024, 1, 5),
            datetime(2024, 1, 8),  # Week 2
            datetime(2024, 1, 10),
        ]
        values = [10.0, 12.0, 14.0, 16.0, 18.0]
        
        result = AnalyticsEngine.aggregate_by_period(dates, values, "weekly")
        
        assert len(result) == 2
        
        # Week 1: mean of 10, 12, 14 = 12
        week1 = result[0]
        assert week1["value"] == 12.0
        assert week1["min"] == 10.0
        assert week1["max"] == 14.0
        assert week1["count"] == 3
        
        # Week 2: mean of 16, 18 = 17
        week2 = result[1]
        assert week2["value"] == 17.0
        assert week2["count"] == 2
    
    def test_aggregate_by_period_monthly(self):
        """Test monthly aggregation"""
        # 3 months of data
        dates = [
            datetime(2024, 1, 5),
            datetime(2024, 1, 20),
            datetime(2024, 2, 10),
            datetime(2024, 3, 15),
            datetime(2024, 3, 25),
        ]
        values = [10.0, 12.0, 15.0, 18.0, 20.0]
        
        result = AnalyticsEngine.aggregate_by_period(dates, values, "monthly")
        
        assert len(result) == 3
        
        # January: mean of 10, 12 = 11
        jan = next(r for r in result if r["period"] == "2024-01-31")
        assert jan["value"] == 11.0
        assert jan["count"] == 2
        
        # February: single value
        feb = next(r for r in result if r["period"] == "2024-02-29")
        assert feb["value"] == 15.0
        assert feb["count"] == 1
        
        # March: mean of 18, 20 = 19
        mar = next(r for r in result if r["period"] == "2024-03-31")
        assert mar["value"] == 19.0
        assert mar["count"] == 2
    
    def test_aggregate_by_period_invalid_period(self):
        """Test aggregation with invalid period defaults to weekly"""
        dates = [datetime(2024, 1, 1), datetime(2024, 1, 8)]
        values = [10.0, 20.0]
        
        result = AnalyticsEngine.aggregate_by_period(dates, values, "invalid")
        
        # Should default to weekly
        assert len(result) >= 1


class TestPercentiles:
    """Test percentile band calculation"""
    
    def test_calculate_percentiles_empty(self):
        """Test percentiles with empty data"""
        result = AnalyticsEngine.calculate_percentiles([], [], [10, 50, 90], "monthly")
        assert result == []
    
    def test_calculate_percentiles_single_value(self):
        """Test percentiles with single value per period"""
        dates = [datetime(2024, 1, 15)]
        values = [10.0]
        
        result = AnalyticsEngine.calculate_percentiles(dates, values, [10, 50, 90], "monthly")
        
        assert len(result) == 1
        assert result[0]["p10"] == 10.0
        assert result[0]["p50"] == 10.0
        assert result[0]["p90"] == 10.0
        assert result[0]["count"] == 1
    
    def test_calculate_percentiles_monthly(self):
        """Test monthly percentile calculation"""
        # January: 5 values
        dates = [
            datetime(2024, 1, 5),
            datetime(2024, 1, 10),
            datetime(2024, 1, 15),
            datetime(2024, 1, 20),
            datetime(2024, 1, 25),
        ]
        values = [10.0, 12.0, 14.0, 16.0, 18.0]
        
        result = AnalyticsEngine.calculate_percentiles(dates, values, [10, 50, 90], "monthly")
        
        assert len(result) == 1
        jan = result[0]
        
        assert jan["count"] == 5
        assert jan["p10"] < jan["p50"] < jan["p90"]
        # Median should be around 14
        assert abs(jan["p50"] - 14.0) < 0.1
    
    def test_calculate_percentiles_weekly(self):
        """Test weekly percentile calculation"""
        # 2 weeks
        dates = [
            datetime(2024, 1, 1),
            datetime(2024, 1, 3),
            datetime(2024, 1, 8),
            datetime(2024, 1, 10),
        ]
        values = [10.0, 12.0, 15.0, 18.0]
        
        result = AnalyticsEngine.calculate_percentiles(dates, values, [25, 50, 75], "weekly")
        
        assert len(result) == 2
        
        # Week 1: 10, 12
        week1 = result[0]
        assert week1["count"] == 2
        assert "p25" in week1
        assert "p50" in week1
        assert "p75" in week1
        
        # Week 2: 15, 18
        week2 = result[1]
        assert week2["count"] == 2
    
    def test_calculate_percentiles_custom_percentiles(self):
        """Test percentile calculation with custom percentile values"""
        dates = [datetime(2024, 1, i) for i in range(1, 11)]
        values = [float(i) for i in range(1, 11)]
        
        result = AnalyticsEngine.calculate_percentiles(
            dates, values, [5, 25, 50, 75, 95], "monthly"
        )
        
        assert len(result) == 1
        month = result[0]
        
        assert "p5" in month
        assert "p25" in month
        assert "p50" in month
        assert "p75" in month
        assert "p95" in month
        
        # Percentiles should be ordered
        assert month["p5"] < month["p25"] < month["p50"] < month["p75"] < month["p95"]
