import pandas as pd
import numpy as np


def run_simulation(soil: dict, weather: pd.DataFrame, crop: dict, management: dict) -> dict:
    """
    Simulate STICS-inspired maize model with stage-specific leaf expansion
    and nitrogen-limited growth via a Nitrogen Nutrition Index (NNI).
    """
    # Unpack soil layers
    layers = soil['layers']
    n_layers = len(layers)
    FC = np.array([lyr['field_capacity'] for lyr in layers], float)
    WP = np.array([lyr['wilting_point'] for lyr in layers], float)
    thickness = np.array([lyr['depth_bottom'] - lyr['depth_top'] for lyr in layers], float)

    # Initialize states
    water_mm = FC * thickness * 1000  # start at field capacity (mm)
    Nmin = np.full(n_layers, management['initial_nitrate_kgN_ha'] / n_layers)
    biomass = 0.0
    TT_accum = 0.0
    TT_base = 8.0

    # Vegetative stage duration (days)
    veg_days = crop['Cycle_days'] * 0.5
    base_dLAI = crop['Max_LAI'] / veg_days

    # Prepare daily record
    dates = pd.to_datetime(weather['DATE'], format='%Y%m%d')
    n_days = len(dates)
    daily = pd.DataFrame({
        'date': dates,
        'TT': np.zeros(n_days),
        'LAI': np.zeros(n_days),
        'Biomass': np.zeros(n_days),
        'SWC': np.zeros(n_days),
        'Nmin_total': np.zeros(n_days),
        'ETa': np.zeros(n_days)
    })

    # Uniform root distribution
    root_frac = thickness / thickness.sum()

    # Management schedules
    fert = {pd.to_datetime(ev['date']): ev['amount_kgN_ha'] for ev in management['fertilization']}
    irr = {pd.to_datetime(ev['date']): ev['amount_mm'] for ev in management['irrigation']}
    sow_date = pd.to_datetime(management['sowing']['date'])

    # Mineralization and leaching parameters
    mineralization_rate = 0.5  # kg N/ha/day
    leaching_factor = 0.1      # fraction of percolated N lost

    # Simulation loop
    for i, day in enumerate(dates):
        tmin, tmax = weather.loc[i, ['TMIN', 'TMAX']]
        rad = weather.loc[i, 'RADIATION']
        rain = weather.loc[i, 'RAIN']

        # 1. Thermal time accumulation
        dTT = max(0.0, (tmin + tmax) / 2.0 - TT_base)
        TT_accum += dTT
        daily.at[i, 'TT'] = TT_accum

        # 2. Events: fertilization and irrigation
        if day in fert:
            Nmin += fert[day] / n_layers
        if day in irr:
            water_mm += irr[day] * root_frac

        # 3. Water balance (Hargreaves + simple redistribution)
        PET = 0.0023 * (tmax - tmin)**0.5 * ((tmax + tmin) / 2.0 + 17.8) * rad
        avail_frac = np.clip((water_mm / 1000.0 - WP) / (FC - WP), 0.0, 1.0)
        ETa_layers = PET * avail_frac
        ETa = ETa_layers.sum()
        water_mm = np.maximum(water_mm - ETa_layers, 0.0)
        water_mm += rain * root_frac
        daily.at[i, 'ETa'] = ETa
        daily.at[i, 'SWC'] = water_mm.sum()

        # 4. Potential LAI & biomass increments
        if i == 0:
            LAI = min(base_dLAI, crop['Max_LAI'])
        else:
            if (day - sow_date).days <= veg_days:
                LAI = min(daily['LAI'].iloc[i-1] + base_dLAI, crop['Max_LAI'])
            else:
                LAI = daily['LAI'].iloc[i-1]
        IPAR = rad * (1.0 - np.exp(-0.65 * LAI))
        potential_dB = crop['Light_Use_Efficiency'] * IPAR * management['sowing']['density']

        # 5. Nitrogen uptake and compute NNI
        # Demand based on potential biomass increment
        Ndemand = potential_dB * 10.0 * 0.03  # g/m2→kg/ha with 3% N
        supply = Nmin.sum()
        uptake = min(Ndemand, supply)
        Nmin -= uptake * root_frac
        # mineralization
        Nmin += mineralization_rate / n_layers
        # leaching
        percol = np.maximum(water_mm - FC * thickness * 1000.0, 0.0)
        leach = leaching_factor * percol * (Nmin / (water_mm + 1e-6))
        Nmin -= leach
        Nmin = np.maximum(Nmin, 0.0)
        daily.at[i, 'Nmin_total'] = Nmin.sum()

        # Compute NNI
        NNI = min(1.0, supply / (Ndemand + 1e-6))

        # 6. Apply NNI to growth
        dB = potential_dB * NNI
        biomass += dB
        daily.at[i, 'Biomass'] = biomass
        daily.at[i, 'LAI'] = LAI * NNI

        # Terminate at maturity
        if (day - sow_date).days >= crop['Cycle_days']:
            break

    # Summary outputs
    summary = {
        'final_biomass': biomass,
        'grain_yield_est': biomass * 0.5,
        'total_ETa': daily['ETa'].sum(),
        'total_uptake_N': management['initial_nitrate_kgN_ha'] - Nmin.sum(),
        'days_simulated': i + 1
    }
    return {'daily': daily, 'summary': summary}