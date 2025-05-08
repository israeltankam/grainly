# preprocess.py

import pandas as pd
from datetime import datetime, timedelta
from models.weather_fetch import fetch_weather


def prepare_inputs(session_state: dict, varieties_csv: str = "src/data/maize_varieties.csv") -> dict:
    """
    Prepare inputs for STICS model based on user session state, freshly fetched weather data,
    and maize variety parameters.

    Args:
        session_state: Dict containing keys:
            - variety: str
            - sowing_date: datetime.date
            - sowing_depth: float (cm)
            - density: float (plants/m2)
            - area: float (ha)
            - use_expert_soil: bool
            - soil_type: str
            - soil_layers: pd.DataFrame
            - fert_schedule: pd.DataFrame (cols: date, amount)
            - irr_schedule: pd.DataFrame (cols: date, amount)
            - initial_nitrate: float (kg N/ha)
            - location_coords: (lat, lon) tuple
        varieties_csv: Path to CSV of maize variety parameters

    Returns:
        stics_inputs: dict of structured parameters for STICS:
            - crop: dict of plant parameters
            - soil: dict of soil profile
            - management: dict of events
            - weather: formatted DataFrame
    """
    # 1. Load variety parameters
    var_df = pd.read_csv(varieties_csv, encoding='ISO-8859-1')
    try:
        var = var_df[var_df['Variety'] == session_state['variety']].iloc[0]
    except IndexError:
        raise ValueError(f"Variety '{session_state['variety']}' not found in {varieties_csv}")

    crop_params = {
        'name': var['Variety'],
        'FAO_Maturity_Group': int(var['FAO_Maturity_Group']),
        'Cycle_days': int(var['Cycle_days']),
        'Light_Use_Efficiency': float(var['Light_Use_Efficiency']),
        'Max_LAI': float(var['Max_LAI']),
        'Root_Depth': float(var['Root_Depth']),
        'N_Uptake_Efficiency': float(var['N_Uptake_Efficiency'])
    }

    # 2. Soil profile
    if session_state.get('use_expert_soil'):
        soil_layers = session_state['soil_layers'].to_dict(orient='records')
    else:
        from pages.main.get_start import _SOIL_TABLE
        stype = session_state['soil_type'].lower()
        props = _SOIL_TABLE.get(stype)
        if props is None:
            raise ValueError(f"Soil type '{stype}' not in _SOIL_TABLE")
        soil_layers = [{
            'depth_top': 0.0,
            'depth_bottom': 1.5,
            'texture': stype,
            'field_capacity': props['field_capacity'],
            'wilting_point': props['wilting_point']
        }]
    soil_profile = {'layers': soil_layers}

    # 3. Management events
    sow_date = session_state['sowing_date']
    sow_event = {
        'date': sow_date.isoformat(),
        'depth_cm': float(session_state['sowing_depth']),
        'density': float(session_state['density'])
    }

    fert_events = [
        {'date': pd.to_datetime(row['date']).date().isoformat(),
         'amount_kgN_ha': float(row['amount'])}
        for _, row in session_state['fert_schedule'].iterrows()
    ]

    irr_events = [
        {'date': pd.to_datetime(row['date']).date().isoformat(),
         'amount_mm': float(row['amount'])}
        for _, row in session_state['irr_schedule'].iterrows()
    ]

    management = {
        'sowing': sow_event,
        'initial_nitrate_kgN_ha': float(session_state['initial_nitrate']),
        'fertilization': fert_events,
        'irrigation': irr_events
    }

    # 4. Fetch and format weather
    lat, lon = session_state.get('location_coords', (None, None))
    if lat is None or lon is None:
        raise ValueError("Location coordinates missing; cannot fetch weather.")
    start_date = sow_date
    end_date = sow_date + timedelta(days=crop_params['Cycle_days'])
    weather_df = fetch_weather(lat, lon,
                               start_date.isoformat(),
                               end_date.isoformat())
    # Rename and format
    weather = weather_df.rename(columns={
        'date': 'DATE', 'tmin': 'TMIN', 'tmax': 'TMAX',
        'precipitation': 'RAIN', 'radiation': 'RADIATION'
    })
    weather['DATE'] = pd.to_datetime(weather['DATE']).dt.strftime('%Y%m%d')

    return {
        'crop': crop_params,
        'soil': soil_profile,
        'management': management,
        'weather': weather
    }
