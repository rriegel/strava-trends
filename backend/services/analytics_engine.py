import pandas as pd
import numpy as np
from scipy import stats
from typing import List, Dict, Optional
from datetime import datetime

class AnalyticsEngine:
    """Compute analytics and trends from activity data"""
    
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
        # Simple adjustment: add 10 seconds per km per 1% grade
        adjustment = grade * 10 / 60  # Convert to m/s adjustment
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
    
    @staticmethod
    def calculate_trend(
        dates: List[datetime],
        values: List[float]
    ) -> Dict:
        """Calculate linear regression trend"""
        if len(dates) < 2:
            return {"slope": 0, "direction": "stable", "r_squared": 0}
        
        # Convert dates to numeric (days since first date)
        x = np.array([(d - dates[0]).days for d in dates])
        y = np.array(values)
        
        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # Determine direction
        if slope > 0.01:
            direction = "increasing"
        elif slope < -0.01:
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
            freq = "M"
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
        elif period == "monthly":
            freq = "M"
        else:
            freq = "M"
        
        result = []
        for date, group in df.resample(freq):
            if len(group) > 0:
                band = {"date": date.strftime("%Y-%m-%d"), "count": len(group)}
                for p in percentiles:
                    band[f"p{p}"] = float(group['value'].quantile(p / 100))
                result.append(band)
        
        return result
