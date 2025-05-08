#weather_fetch.py

import requests
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta


def fetch_historical(lat, lon, start_date, end_date, timezone="Europe/Paris"):
    """
    Fetch past weather data using the Open-Meteo Archive API.
    """
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        "&daily=temperature_2m_min,temperature_2m_max,precipitation_sum,shortwave_radiation_sum"
        f"&timezone={timezone}"
    )
    r = requests.get(url)
    r.raise_for_status()
    data = r.json().get("daily", {})

    radiation_raw = data.get("shortwave_radiation_sum", [])
    radiation = [(x * 0.0036) if x is not None else np.nan for x in radiation_raw]

    df = pd.DataFrame({
        "date": pd.to_datetime(data.get("time", [])),
        "tmin": data.get("temperature_2m_min", []),
        "tmax": data.get("temperature_2m_max", []),
        "precipitation": data.get("precipitation_sum", []),
        "radiation": radiation,
    })
    return df


def fetch_moving_avg_forecast(lat, lon, start_date, end_date, years=4):
    """
    Estimate future weather by averaging historical data for the same calendar days
    over the previous `years` years.

    Returns a DataFrame covering [start_date..end_date], with columns: date, tmin, tmax,
    precipitation, radiation.
    """
    sd = pd.to_datetime(start_date).date()
    ed = pd.to_datetime(end_date).date()
    frames = []

    # Collect historical series for each of the previous `years` years
    for y in range(1, years+1):
        year_offset_sd = sd.replace(year=sd.year - y)
        year_offset_ed = ed.replace(year=ed.year - y)
        df_hist = fetch_historical(lat, lon,
                                   year_offset_sd.isoformat(),
                                   year_offset_ed.isoformat())
        # Align dates to forecast year
        df_hist['day_of_year'] = df_hist['date'].dt.strftime('%m-%d')
        frames.append(df_hist)

    # Concatenate and compute mean for each calendar day
    df_concat = pd.concat(frames, ignore_index=True)
    df_avg = df_concat.groupby('day_of_year').agg({
        'tmin': 'mean',
        'tmax': 'mean',
        'precipitation': 'mean',
        'radiation': 'mean'
    }).reset_index()
    # Reconstruct forecast dates
    forecast_days = (ed - sd).days + 1
    dates = [sd + timedelta(days=i) for i in range(forecast_days)]
    doy = [d.strftime('%m-%d') for d in dates]
    df_forecast = pd.DataFrame({
        'date': dates,
        'day_of_year': doy
    }).merge(df_avg, on='day_of_year', how='left')
    return df_forecast[['date', 'tmin', 'tmax', 'precipitation', 'radiation']]


def fetch_weather(lat, lon, start_date, end_date):
    """
    Unified function: fetch historical up to today-1, then estimate future via moving average.

    Returns a DataFrame with columns: date, tmin, tmax, precipitation, radiation.
    """
    sd = pd.to_datetime(start_date).date()
    ed = pd.to_datetime(end_date).date()
    today = date.today()
    yesterday = today - timedelta(days=1)

    parts = []
    # Historical part
    if sd <= yesterday:
        hist_end = min(ed, yesterday)
        parts.append(fetch_historical(lat, lon, sd.isoformat(), hist_end.isoformat()))

    # Future estimate part
    if ed >= today:
        future_start = max(sd, today)
        parts.append(fetch_moving_avg_forecast(lat, lon,
                                               future_start.isoformat(),
                                               ed.isoformat()))

    if not parts:
        raise ValueError("Requested range yields no data (all dates are in the future?).")

    df = pd.concat(parts).reset_index(drop=True)
    return df


# Tests
def _test_synthetic():
    # Synthetic historical stub for deterministic test
    def stub_hist(lat, lon, start, end):
        dates = pd.date_range(start, end)
        return pd.DataFrame({
            'date': dates,
            'tmin': np.arange(len(dates)),
            'tmax': np.arange(len(dates)) + 10,
            'precipitation': np.ones(len(dates)),
            'radiation': np.ones(len(dates)) * 5
        })

    global fetch_historical
    real_hist = fetch_historical
    fetch_historical = stub_hist

    # Test forecast for 3-day window, averaging stub years
    today = date.today()
    sd = (today + timedelta(days=1)).isoformat()
    ed = (today + timedelta(days=3)).isoformat()
    df = fetch_weather(0, 0, sd, ed)
    assert len(df) == 3 + 0  # no historical
    # tmin average of 0..2 across 4 years => same pattern
    print("Synthetic forecast test passed", df)

    fetch_historical = real_hist

if __name__ == "__main__":
    _test_synthetic()
