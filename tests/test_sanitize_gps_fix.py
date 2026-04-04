
import pandas as pd
import pytest

from tools.sanitize_gps import sanitize_dataframe


def test_sanitize_dataframe_short_activity():
    """Verify that sanitize_dataframe handles short activities gracefully."""
    # Create an activity shorter than 1000m (default truncation 500+500)
    df = pd.DataFrame({
        'distance_cumulative_m': [0, 100, 200, 300],
        'lat': [1, 1.1, 1.2, 1.3],
        'lon': [2, 2.1, 2.2, 2.3],
    })

    with pytest.warns(UserWarning, match="Activity total distance .* is shorter than truncation"):
        df_safe = sanitize_dataframe(df, truncate_start_m=500, truncate_end_m=500)

    assert df_safe.empty
    assert 'lat' not in df_safe.columns
    assert 'lon' not in df_safe.columns
    assert 'distance_cumulative_m' in df_safe.columns
