import pandas as pd
import numpy as np
# Pyright: scipy 1.14 ships no py.typed and scipy-stubs (installed for >=1.15)
# types LinregressResult attributes as unknown, so float(reg.slope) etc. trigger
# reportAttributeAccessIssue. Stub-coverage gap, not a code defect — regression
# math is unit-tested. Revisit after upgrading scipy >= 1.15.
from scipy import stats  # type: ignore[reportAttributeAccessIssue]
from typing import List, Dict, Optional
from datetime import datetime

class AnalyticsEngine:
    """Compute analytics and trends from activity data"""
    
    # Metrics stored as speed (m/s) but displayed as pace (min/km)
    SPEED_METRICS = {"average_speed"}
    # Metrics stored as pace (min/km)
    PACE_METRICS = {"grade_adjusted_pace"}
    
    @staticmethod
    def speed_to_pace(speed_mps: float) -> float:
        """
        Convert speed (m/s) to pace (min/km).
        
        This is a non-linear (reciprocal) transformation: pace = 1000 / speed / 60.
        Because it is non-linear, statistics (trend, R²) must be computed on the
        values that are actually displayed — hence this conversion happens in the
        service layer BEFORE calculate_trend is called, not after.
        """
        if not speed_mps or speed_mps <= 0:
            return 0.0
        return 1000.0 / speed_mps / 60.0
    
    @classmethod
    def to_display_value(cls, metric_type: str, value: float) -> float:
        """Convert a stored metric value to its display unit (pace metrics -> min/km)."""
        if metric_type in cls.SPEED_METRICS:
            return cls.speed_to_pace(value)
        return float(value)
    
    @classmethod
    def direction_threshold(cls, metric_type: str) -> float:
        """
        Slope threshold (per day) below which a trend counts as 'stable'.
        
        Unit-dependent: 0.01 min/km/day is ~1s/km slower per day, while 0.01
        bpm/day is imperceptible. Per-metric thresholds keep 'stable' meaningful.
        """
        if metric_type in cls.SPEED_METRICS or metric_type in cls.PACE_METRICS:
            return 0.005   # min/km per day (~3s/km per week)
        if metric_type == "average_heartrate":
            return 0.1     # bpm per day
        if metric_type == "average_cadence":
            return 0.1     # spm per day
        return 0.01
    
    @staticmethod
    def compute_hr_pace_ratio(avg_hr: float, avg_pace: float) -> float:
        """Compute HR/pace ratio (lower = fitter)"""
        if avg_pace == 0:
            return 0
        return avg_hr / avg_pace
    
    @staticmethod
    def compute_grade_adjusted_pace(
        pace: float,
        elevation_gain: float,
        distance: float
    ) -> float:
        """Compute grade-adjusted pace (accounts for hills)"""
        if distance == 0:
            return pace
        
        grade = elevation_gain / distance
        # Simple adjustment: add 10 seconds per km per 1% grade (converted to minutes)
        adjustment = grade * 10 / 60
        return pace + adjustment
    
    @staticmethod
    def compute_running_economy(
        avg_hr: float,
        avg_pace: float,
        weight_kg: float = 70
    ) -> float:
        """Compute running economy (HR per unit of speed per kg)"""
        if avg_pace == 0 or weight_kg == 0:
            return 0
        return avg_hr / (avg_pace * weight_kg)
    
    @staticmethod
    def compute_heart_rate_drift(
        first_half_hr: float,
        second_half_hr: float
    ) -> float:
        """Compute heart rate drift (cardiac drift during steady effort)"""
        return second_half_hr - first_half_hr
    
    @classmethod
    def calculate_trend(
        cls,
        dates: List[datetime],
        values: List[float],
        metric_type: Optional[str] = None
    ) -> Dict:
        """
        Calculate linear regression trend.
        
        Args:
            dates: Activity dates (x axis)
            values: Metric values (y axis) — MUST already be in display units
                    (min/km for pace metrics). Use to_display_value() first.
            metric_type: Optional metric type for a unit-aware 'stable' threshold.
        
        The R² and direction describe the values passed in. For pace metrics,
        'increasing' means slowing down (pace getting higher); the frontend
        colors accordingly.
        """
        if len(dates) < 2:
            return {"slope": 0, "direction": "stable", "r_squared": 0}
        
        # Convert dates to numeric (days since first date, fractional)
        x = np.array([(d - dates[0]).total_seconds() / 86400.0 for d in dates])
        y = np.array(values, dtype=float)
        
        # Linear regression
        reg = stats.linregress(x, y)
        slope = float(reg.slope)  # type: ignore[reportAttributeAccessIssue]
        intercept = float(reg.intercept)  # type: ignore[reportAttributeAccessIssue]
        r_value = float(reg.rvalue)  # type: ignore[reportAttributeAccessIssue]
        p_value = float(reg.pvalue)  # type: ignore[reportAttributeAccessIssue]
        
        # Determine direction (threshold depends on metric units)
        threshold = cls.direction_threshold(metric_type) if metric_type else 0.01
        if slope > threshold:
            direction = "increasing"
        elif slope < -threshold:
            direction = "decreasing"
        else:
            direction = "stable"
        
        return {
            "slope": float(slope),
            "intercept": float(intercept),
            "r_squared": float(r_value ** 2),
            "direction": direction,
            "p_value": float(p_value)
        }
    
    @staticmethod
    def aggregate_by_period(
        dates: List[datetime],
        values: List[float],
        period: str = "weekly"
    ) -> List[Dict]:
        """Aggregate data by time period (daily, weekly, monthly)"""
        df = pd.DataFrame({"date": dates, "value": values})
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        if period == "daily":
            freq = "D"
        elif period == "weekly":
            freq = "W"
        elif period == "monthly":
            freq = "ME"
        else:
            freq = "W"
        
        aggregated = df.resample(freq).agg({
            "value": ["mean", "min", "max", "count"]
        })
        
        result = []
        for date, row in aggregated.iterrows():
            if row['value']['count'] > 0:
                result.append({
                    "period": date.strftime("%Y-%m-%d"),
                    "value": float(row['value']['mean']),
                    "min": float(row['value']['min']),
                    "max": float(row['value']['max']),
                    "count": int(row['value']['count'])
                })
        
        return result
    
    @staticmethod
    def calculate_percentiles(
        dates: List[datetime],
        values: List[float],
        percentiles: List[int] = [10, 50, 90],
        period: str = "monthly"
    ) -> List[Dict]:
        """Calculate percentile bands over time"""
        df = pd.DataFrame({"date": dates, "value": values})
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        if period == "weekly":
            freq = "W"
        elif period == "daily":
            freq = "D"
        else:
            # monthly (default)
            freq = "ME"
        
        result = []
        for date, group in df.resample(freq):
            if len(group) > 0:
                band = {"date": date.strftime("%Y-%m-%d"), "count": len(group)}
                for p in percentiles:
                    band[f"p{p}"] = float(group['value'].quantile(p / 100))
                result.append(band)
        
        return result
