"""
Tests for effort classifier service
"""
import pytest
from services.effort_classifier import EffortClassifier


class TestEffortClassifier:
    """Test effort classification and zone calculation"""
    
    def test_zone_classification(self, db_session, sample_user):
        """Test HR value classification into zones"""
        classifier = EffortClassifier(db_session)
        max_hr = 200
        
        # Zone 1: Easy (50-60%)
        assert classifier.classify_hr_value(100, max_hr) == 'easy'
        assert classifier.classify_hr_value(110, max_hr) == 'easy'
        assert classifier.classify_hr_value(119, max_hr) == 'easy'
        
        # Zone 2: Moderate (60-70%)
        assert classifier.classify_hr_value(120, max_hr) == 'moderate'
        assert classifier.classify_hr_value(130, max_hr) == 'moderate'
        assert classifier.classify_hr_value(139, max_hr) == 'moderate'
        
        # Zone 3: Threshold (70-80%)
        assert classifier.classify_hr_value(140, max_hr) == 'threshold'
        assert classifier.classify_hr_value(150, max_hr) == 'threshold'
        assert classifier.classify_hr_value(159, max_hr) == 'threshold'
        
        # Zone 4: VO2 Max (80-90%)
        assert classifier.classify_hr_value(160, max_hr) == 'vo2max'
        assert classifier.classify_hr_value(170, max_hr) == 'vo2max'
        assert classifier.classify_hr_value(179, max_hr) == 'vo2max'
        
        # Zone 5: Anaerobic (90-100%)
        assert classifier.classify_hr_value(180, max_hr) == 'anaerobic'
        assert classifier.classify_hr_value(190, max_hr) == 'anaerobic'
        assert classifier.classify_hr_value(200, max_hr) == 'anaerobic'
    
    def test_zone_classification_edge_cases(self, db_session, sample_user):
        """Test edge cases in zone classification"""
        classifier = EffortClassifier(db_session)
        max_hr = 200
        
        # Below zone 1
        assert classifier.classify_hr_value(50, max_hr) == 'easy'
        assert classifier.classify_hr_value(99, max_hr) == 'easy'
        
        # Above zone 5
        assert classifier.classify_hr_value(201, max_hr) == 'anaerobic'
        assert classifier.classify_hr_value(220, max_hr) == 'anaerobic'
    
    def test_time_in_zones_calculation(self, db_session, sample_user):
        """Test time calculation across zones"""
        classifier = EffortClassifier(db_session)
        max_hr = 200
        
        # 10 samples: 3 easy, 4 moderate, 2 threshold, 1 vo2max
        hr_stream = [110, 115, 105, 125, 130, 135, 128, 145, 150, 165]
        
        zone_times = classifier.calculate_time_in_zones(hr_stream, max_hr)
        
        # Each sample is 1 second by default
        assert zone_times['easy'] == 3.0
        assert zone_times['moderate'] == 4.0
        assert zone_times['threshold'] == 2.0
        assert zone_times['vo2max'] == 1.0
        assert zone_times['anaerobic'] == 0.0
    
    def test_time_in_zones_custom_resolution(self, db_session, sample_user):
        """Test time calculation with custom time per sample"""
        classifier = EffortClassifier(db_session)
        max_hr = 200
        
        hr_stream = [110, 130, 150]  # easy, moderate, threshold
        zone_times = classifier.calculate_time_in_zones(hr_stream, max_hr, time_per_sample=5.0)
        
        # Each sample represents 5 seconds
        assert zone_times['easy'] == 5.0
        assert zone_times['moderate'] == 5.0
        assert zone_times['threshold'] == 5.0
    
    def test_get_max_hr_from_user(self, db_session, sample_user, sample_activity):
        """Test max HR detection prioritizes user setting"""
        from models.user import User
        
        # Set user max HR
        sample_user.max_hr = 190
        db_session.commit()
        
        # Set activity max HR (should be ignored)
        sample_activity.max_heartrate = 185
        db_session.commit()
        
        classifier = EffortClassifier(db_session)
        max_hr = classifier.get_max_hr(sample_user.id, sample_activity)
        
        assert max_hr == 190
    
    def test_get_max_hr_from_activity(self, db_session, sample_user, sample_activity):
        """Test max HR falls back to activity data"""
        # User has no max HR set
        sample_user.max_hr = None
        db_session.commit()
        
        # Activity has max HR
        sample_activity.max_heartrate = 185
        db_session.commit()
        
        classifier = EffortClassifier(db_session)
        max_hr = classifier.get_max_hr(sample_user.id, sample_activity)
        
        assert max_hr == 185
    
    def test_get_max_hr_from_stream(self, db_session, sample_user, sample_activity):
        """Test max HR falls back to HR stream data"""
        from models.activity_stream import ActivityStream
        
        # User and activity have no max HR
        sample_user.max_hr = None
        sample_activity.max_heartrate = None
        db_session.commit()
        
        # Create HR stream with max value
        hr_stream = ActivityStream(
            user_id=sample_user.id,
            activity_id=sample_activity.id,
            stream_type='heartrate',
            data=[150, 160, 170, 180, 175],
            series_type='time',
            original_size=5
        )
        db_session.add(hr_stream)
        db_session.commit()
        
        classifier = EffortClassifier(db_session)
        max_hr = classifier.get_max_hr(sample_user.id, sample_activity)
        
        assert max_hr == 180
    
    def test_get_max_hr_no_data(self, db_session, sample_user, sample_activity):
        """Test max HR returns None when no data available"""
        sample_user.max_hr = None
        sample_activity.max_heartrate = None
        db_session.commit()
        
        classifier = EffortClassifier(db_session)
        max_hr = classifier.get_max_hr(sample_user.id, sample_activity)
        
        assert max_hr is None
    
    def test_analyze_activity_no_hr_data(self, db_session, sample_user, sample_activity):
        """Test analyze returns None when no HR data"""
        sample_activity.max_heartrate = None
        db_session.commit()
        
        classifier = EffortClassifier(db_session)
        result = classifier.analyze_activity(sample_activity.id)
        
        assert result is None
    
    def test_analyze_activity_creates_effort_groups(self, db_session, sample_user, sample_activity):
        """Test analyze creates effort_group records"""
        from models.activity_stream import ActivityStream
        from models.effort_group import EffortGroup
        
        # Set up HR stream: 2 easy, 2 moderate, 1 threshold, 2 vo2max
        hr_stream = ActivityStream(
            user_id=sample_user.id,
            activity_id=sample_activity.id,
            stream_type='heartrate',
            data=[110, 115, 130, 135, 150, 165, 170],
            series_type='time',
            original_size=7
        )
        db_session.add(hr_stream)
        
        sample_activity.max_heartrate = 200
        db_session.commit()
        
        classifier = EffortClassifier(db_session)
        result = classifier.analyze_activity(sample_activity.id)
        
        # Check result structure
        assert result is not None
        assert result['max_hr'] == 200
        # easy=2, moderate=2, threshold=1, vo2max=2 — easy wins tie (first in dict)
        assert result['dominant_zone'] == 'easy'
        assert result['total_time'] == 7.0
        assert 'zone_times' in result
        assert 'zone_percentages' in result
        
        # Check effort_group records created
        effort_groups = db_session.query(EffortGroup).filter(
            EffortGroup.activity_id == sample_activity.id
        ).all()
        
        assert len(effort_groups) == 4  # easy, moderate, threshold, vo2max
        
        # Verify activity.effort_zone updated
        db_session.refresh(sample_activity)
        assert sample_activity.effort_zone == 'easy'
    
    def test_get_activity_effort(self, db_session, sample_user, sample_activity):
        """Test get_activity_effort retrieves existing analysis"""
        from models.activity_stream import ActivityStream
        from models.effort_group import EffortGroup
        
        # Set up HR stream: 1 easy, 1 moderate, 1 threshold, 1 vo2max
        # With equal time, 'easy' wins as first in dict order
        hr_stream = ActivityStream(
            user_id=sample_user.id,
            activity_id=sample_activity.id,
            stream_type='heartrate',
            data=[110, 130, 150, 170],
            series_type='time',
            original_size=4
        )
        db_session.add(hr_stream)
        
        sample_activity.max_heartrate = 200
        db_session.commit()
        
        classifier = EffortClassifier(db_session)
        classifier.analyze_activity(sample_activity.id)
        
        # Get effort data
        result = classifier.get_activity_effort(sample_activity.id)
        
        assert result is not None
        assert result['max_hr'] == 200
        assert result['dominant_zone'] == 'easy'  # all zones equal, easy first
        assert result['total_time'] == 4.0
        assert 'zone_labels' in result
        assert len(result['zone_times']) == 4
    
    def test_get_activity_effort_not_analyzed(self, db_session, sample_user, sample_activity):
        """Test get_activity_effort returns None when not analyzed"""
        classifier = EffortClassifier(db_session)
        result = classifier.get_activity_effort(sample_activity.id)
        
        assert result is None
