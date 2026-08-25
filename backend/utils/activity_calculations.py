"""
Common calculation utilities for activity file parsing.
Shared logic for FIT, GPX, and TCX parsers.
"""
from typing import List, Tuple, Optional
from datetime import datetime


# Thresholds for filtering GPS noise
SPEED_THRESHOLD = 0.5  # m/s - consider stationary below this speed
ELEVATION_WINDOW = 5  # Moving average window size for elevation smoothing
MIN_GAIN_THRESHOLD = 2.0  # meters - minimum climb to count as real elevation gain


def calculate_moving_time(
    timestamps: List[datetime],
    distances: List[float],
    speed_threshold: float = SPEED_THRESHOLD
) -> float:
    """
    Calculate moving time by filtering out stationary periods.
    
    Args:
        timestamps: List of datetime objects for each trackpoint
        distances: List of cumulative distances (meters) at each trackpoint
        speed_threshold: Minimum speed (m/s) to consider as moving
    
    Returns:
        Moving time in seconds
    """
    if len(timestamps) < 2 or len(distances) < 2:
        return 0.0
    
    moving_time = 0.0
    
    for i in range(1, len(timestamps)):
        if timestamps[i] and timestamps[i-1]:
            time_diff = (timestamps[i] - timestamps[i-1]).total_seconds()
            
            if time_diff > 0:
                # Calculate segment distance
                segment_distance = distances[i] - distances[i-1]
                
                if segment_distance > 0:
                    speed = segment_distance / time_diff
                    
                    # Only count time if speed exceeds threshold (moving)
                    if speed >= speed_threshold:
                        moving_time += time_diff
    
    return moving_time


def calculate_distance_from_latlng(latlng_points: List[Tuple[float, float]]) -> float:
    """
    Calculate total distance from GPS coordinates using 2D (horizontal) distance.
    
    Uses the Haversine formula for accurate distance calculation between lat/lng points.
    
    Args:
        latlng_points: List of (latitude, longitude) tuples in degrees
    
    Returns:
        Total distance in meters
    """
    if len(latlng_points) < 2:
        return 0.0
    
    total_distance = 0.0
    
    for i in range(1, len(latlng_points)):
        lat1, lon1 = latlng_points[i-1]
        lat2, lon2 = latlng_points[i]
        
        if lat1 is not None and lon1 is not None and lat2 is not None and lon2 is not None:
            # Haversine formula
            from math import radians, sin, cos, sqrt, atan2
            
            R = 6371000  # Earth's radius in meters
            
            lat1_rad = radians(lat1)
            lat2_rad = radians(lat2)
            delta_lat = radians(lat2 - lat1)
            delta_lon = radians(lon2 - lon1)
            
            a = sin(delta_lat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2)**2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            
            total_distance += R * c
    
    return total_distance


def calculate_max_speed(
    timestamps: List[datetime],
    distances: List[float]
) -> float:
    """
    Calculate maximum speed from trackpoint timestamps and distances.
    
    Args:
        timestamps: List of datetime objects for each trackpoint
        distances: List of cumulative distances (meters) at each trackpoint
    
    Returns:
        Maximum speed in m/s
    """
    if len(timestamps) < 2 or len(distances) < 2:
        return 0.0
    
    max_speed = 0.0
    
    for i in range(1, len(timestamps)):
        if timestamps[i] and timestamps[i-1]:
            time_diff = (timestamps[i] - timestamps[i-1]).total_seconds()
            
            if time_diff > 0:
                segment_distance = distances[i] - distances[i-1]
                
                if segment_distance > 0:
                    speed = segment_distance / time_diff
                    max_speed = max(max_speed, speed)
    
    return max_speed


def calculate_elevation_gain(elevation_points: List[float], window: int = ELEVATION_WINDOW) -> float:
    """
    Calculate elevation gain using hysteresis/peak detection to reduce GPS noise.
    
    This approach tracks elevation peaks and only counts gain when climbing
    above a previous low point by a meaningful threshold, reducing false
    positives from GPS drift.
    
    Args:
        elevation_points: List of elevation values in order
        window: Moving average window size for initial smoothing (default 5)
    
    Returns:
        Total elevation gain in meters
    """
    if len(elevation_points) < 2:
        return 0.0
    
    # Step 1: Apply moving average smoothing to reduce high-frequency noise
    smoothed = []
    for i in range(len(elevation_points)):
        start = max(0, i - window // 2)
        end = min(len(elevation_points), i + window // 2 + 1)
        window_points = elevation_points[start:end]
        smoothed.append(sum(window_points) / len(window_points))
    
    # Step 2: Hysteresis/peak detection
    # Only count elevation gain when we climb above a valley by a threshold
    total_gain = 0.0
    valley = smoothed[0]  # Track the lowest point since last peak
    
    for i in range(1, len(smoothed)):
        current = smoothed[i]
        
        # If we've climbed above the valley by the threshold, count the gain
        if current >= valley + MIN_GAIN_THRESHOLD:
            total_gain += (current - valley)
            valley = current  # Reset valley to current peak
        elif current < valley:
            # We're descending, update the valley
            valley = current
    
    return total_gain
