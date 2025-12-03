"""
Tests for Environment Module (Weather Integration)
==================================================

Tests weather API integration, caching, and WMO code translation.
Uses mocking to avoid actual API calls during testing.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import pandas as pd

from biosystems.environment.weather import (
    get_weather_description,
    make_json_serializable,
    WeatherCache,
    fetch_weather_open_meteo,
)


class TestGetWeatherDescription:
    """Test WMO weather code translation."""
    
    def test_clear_sky(self):
        """Test clear sky code."""
        desc = get_weather_description(0)
        assert desc == "Clear sky"
    
    def test_rain(self):
        """Test rain codes."""
        assert get_weather_description(61) == "Slight rain"
        assert get_weather_description(63) == "Moderate rain"
        assert get_weather_description(65) == "Heavy rain"
    
    def test_thunderstorm(self):
        """Test thunderstorm code."""
        desc = get_weather_description(95)
        assert "Thunderstorm" in desc
    
    def test_none_value(self):
        """Test handling of None."""
        desc = get_weather_description(None)
        assert desc == "Unknown"
    
    def test_invalid_code(self):
        """Test handling of invalid code."""
        desc = get_weather_description(999)
        assert "Unknown weather code" in desc
    
    def test_string_code(self):
        """Test handling of string input."""
        desc = get_weather_description("61")
        assert desc == "Slight rain"


class TestMakeJSONSerializable:
    """Test JSON serialization helper."""
    
    def test_dict_with_numpy(self):
        """Test dict containing numpy arrays."""
        import numpy as np
        
        obj = {
            'values': np.array([1, 2, 3]),
            'name': 'test'
        }
        
        result = make_json_serializable(obj)
        
        assert isinstance(result['values'], list)
        assert result['values'] == [1, 2, 3]
        assert result['name'] == 'test'
    
    def test_nested_structure(self):
        """Test nested dict/list structure."""
        import numpy as np
        
        obj = {
            'data': [
                {'array': np.array([1, 2])},
                {'array': np.array([3, 4])}
            ]
        }
        
        result = make_json_serializable(obj)
        
        assert isinstance(result['data'][0]['array'], list)
    
    def test_plain_objects(self):
        """Test that plain objects pass through."""
        obj = {'a': 1, 'b': [2, 3], 'c': 'text'}
        
        result = make_json_serializable(obj)
        
        assert result == obj


class TestWeatherCache:
    """Test weather caching functionality."""
    
    def test_init_new_cache(self):
        """Test creating new cache."""
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            cache_path = Path(f.name)
        
        try:
            cache = WeatherCache(cache_path)
            
            assert cache.cache_path == cache_path
            assert isinstance(cache.cache, pd.DataFrame)
            assert cache.cache.empty
        finally:
            if cache_path.exists():
                cache_path.unlink()
    
    def test_load_existing_cache(self):
        """Test loading existing cache."""
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            cache_path = Path(f.name)
        
        try:
            # Create initial cache with data
            df = pd.DataFrame([{
                'lat': 40.7128,
                'lon': -74.0060,
                'date': '2024-01-01',
                'weather': '{"temp": 20}'
            }])
            df.to_parquet(cache_path, index=False)
            
            # Load cache
            cache = WeatherCache(cache_path)
            
            assert not cache.cache.empty
            assert len(cache.cache) == 1
        finally:
            if cache_path.exists():
                cache_path.unlink()
    
    def test_get_cached_data(self):
        """Test retrieving cached weather data."""
        cache = WeatherCache(None)  # No file, memory only
        
        # Manually add to cache
        cache.cache = pd.DataFrame([{
            'lat': 40.7128,
            'lon': -74.0060,
            'date': '2024-01-01',
            'weather': '{"temp": 20, "code": 0}'
        }])
        
        # Retrieve
        result = cache.get(40.7128, -74.0060, '2024-01-01')
        
        assert result is not None
        assert result['temp'] == 20
    
    def test_get_miss(self):
        """Test cache miss."""
        cache = WeatherCache(None)
        
        result = cache.get(40.7128, -74.0060, '2024-01-01')
        
        assert result is None
    
    def test_set_caches_data(self):
        """Test that set() adds data to cache."""
        cache = WeatherCache(None)  # No file
        
        weather_data = {'temp': 25, 'code': 1}
        cache.set(40.7128, -74.0060, '2024-01-01', weather_data)
        
        # Should be in cache now
        result = cache.get(40.7128, -74.0060, '2024-01-01')
        assert result is not None
        assert result['temp'] == 25


class TestFetchWeatherOpenMeteo:
    """Test weather API fetching with mocking."""
    
    @patch('biosystems.environment.weather.requests.get')
    def test_successful_fetch(self, mock_get):
        """Test successful weather fetch."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'hourly': {
                'temperature_2m': [20.5],
                'weathercode': [1],
                'windspeed_10m': [10.0]
            }
        }
        mock_get.return_value = mock_response
        
        # Fetch weather
        dt = datetime(2024, 1, 1, 12, 0)
        weather, offset = fetch_weather_open_meteo(40.7128, -74.0060, dt)
        
        assert weather is not None
        assert 'hourly' in weather
        assert weather['hourly']['temperature_2m'] == [20.5]
        assert offset is not None
    
    @patch('biosystems.environment.weather.requests.get')
    def test_uses_cache(self, mock_get):
        """Test that cache is used when available."""
        # Create cache with data
        cache = WeatherCache(None)
        cached_weather = {'temp': 20, 'cached': True}
        cache.set(40.7128, -74.0060, '2024-01-01', cached_weather)
        
        # Fetch (should use cache, not call API)
        dt = datetime(2024, 1, 1, 12, 0)
        weather, offset = fetch_weather_open_meteo(40.7128, -74.0060, dt, cache=cache)
        
        assert weather == cached_weather
        assert offset == 0
        # API should not have been called
        mock_get.assert_not_called()
    
    @patch('biosystems.environment.weather.requests.get')
    def test_handles_api_failure(self, mock_get):
        """Test handling of API failures."""
        # Mock failed API response
        mock_get.side_effect = Exception("Network error")
        
        # Should handle gracefully
        dt = datetime(2024, 1, 1, 12, 0)
        weather, offset = fetch_weather_open_meteo(40.7128, -74.0060, dt, max_retries=1)
        
        assert weather is None
        assert offset is None
    
    @patch('biosystems.environment.weather.requests.get')
    def test_retries_on_failure(self, mock_get):
        """Test retry logic."""
        # First call fails, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            'hourly': {
                'temperature_2m': [20.5],
            }
        }
        
        mock_get.side_effect = [
            mock_response_fail,
            mock_response_success
        ]
        
        dt = datetime(2024, 1, 1, 12, 0)
        weather, offset = fetch_weather_open_meteo(40.7128, -74.0060, dt, max_retries=2)
        
        # Should eventually succeed
        assert weather is not None
        assert mock_get.call_count >= 2
    
    @patch('biosystems.environment.weather.requests.get')
    def test_tries_time_variations(self, mock_get):
        """Test that time variations are tried."""
        # All fail except one with time offset
        def side_effect_fn(*args, **kwargs):
            url = args[0]
            # Success only for offset time
            if '11:00:00' in url:  # -1 hour offset
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    'hourly': {'temperature_2m': [20.5]}
                }
                return mock_response
            else:
                mock_response = Mock()
                mock_response.status_code = 404
                return mock_response
        
        mock_get.side_effect = side_effect_fn
        
        dt = datetime(2024, 1, 1, 12, 0)
        weather, offset = fetch_weather_open_meteo(40.7128, -74.0060, dt, max_retries=1)
        
        # Should find data with time offset
        assert weather is not None
        assert offset is not None
