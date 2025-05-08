# simulation.py

import streamlit as st
import pandas as pd
import altair as alt
from models.preprocess import prepare_inputs
from models.stics import run_simulation

# Streamlit page to run STICS simulation and display results
def run_simulation_page():
    st.header("Simulation of maize expected growth")

    # 1. Prepare inputs from session state
    try:
        inputs = prepare_inputs(st.session_state)
    except Exception as e:
        st.error(f"Error preparing inputs: {e}")
        return

    # 2. Run STICS model
    try:
        sim_out = run_simulation(
            soil=inputs['soil'],
            weather=inputs['weather'],
            crop=inputs['crop'],
            management=inputs['management']
        )
    except Exception as e:
        st.error(f"Simulation error: {e}")
        return

    # 3. Store simulation output in session_state
    st.session_state['sim_out'] = sim_out

    daily = sim_out['daily']
    summary = sim_out['summary']

    # 4. Display summary metrics
    st.subheader("Summary Metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Final Biomass (g/m²)", f"{summary['final_biomass']:.1f}")
    col2.metric("Est. Grain Yield (g/m²)", f"{summary['grain_yield_est']:.1f}")
    col3.metric("Total Evapotranspiration (mm)", f"{summary['total_ETa']:.1f}")
    col4.metric("Total N Uptake (kg N/ha)", f"{summary['total_uptake_N']:.1f}")

    # 5. Plot time series with dual axes and legend
    st.subheader("Daily Dynamics")
    df_plot = daily.reset_index()

    tabs = st.tabs(["LAI & Biomass", "Soil Water & Nmin", "ETa"])

    # LAI & Biomass
    with tabs[0]:
        folded = df_plot.melt(id_vars=['date'], value_vars=['LAI','Biomass'], var_name='variable', value_name='value')
        base = alt.Chart(folded).encode(
            x=alt.X('date:T', title='Date'),
            color=alt.Color('variable:N', title='Metric')
        )
        # Layer for LAI (left axis)
        line_lai = base.mark_line().transform_filter(
            alt.datum.variable == 'LAI'
        ).encode(
            y=alt.Y('value:Q', title='LAI', axis=alt.Axis(orient='left'))
        )
        # Layer for Biomass (right axis)
        line_bio = base.mark_line().transform_filter(
            alt.datum.variable == 'Biomass'
        ).encode(
            y=alt.Y('value:Q', title='Biomass (g/m²)', axis=alt.Axis(orient='right'))
        )
        chart = alt.layer(line_lai, line_bio).resolve_scale(y='independent')
        st.altair_chart(chart, use_container_width=True)

    # Soil Water & Nmin
    with tabs[1]:
        folded2 = df_plot.melt(id_vars=['date'], value_vars=['SWC','Nmin_total'], var_name='variable', value_name='value')
        base2 = alt.Chart(folded2).encode(
            x=alt.X('date:T', title='Date'),
            color=alt.Color('variable:N', title='Metric')
        )
        line_swc = base2.mark_line().transform_filter(
            alt.datum.variable == 'SWC'
        ).encode(
            y=alt.Y('value:Q', title='Soil Water Content (mm)', axis=alt.Axis(orient='left'))
        )
        line_n = base2.mark_line().transform_filter(
            alt.datum.variable == 'Nmin_total'
        ).encode(
            y=alt.Y('value:Q', title='Mineral N (kg/ha)', axis=alt.Axis(orient='right'))
        )
        chart2 = alt.layer(line_swc, line_n).resolve_scale(y='independent')
        st.altair_chart(chart2, use_container_width=True)

    # ETa
    with tabs[2]:
        chart3 = alt.Chart(df_plot).mark_line().encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y('ETa:Q', title='Evapotranspiration (mm)'),
            tooltip=['date:T','ETa:Q']
        )
        st.altair_chart(chart3, use_container_width=True)

    # 6. Show raw DataFrame if desired
    with st.expander("Show raw daily data"):
        st.dataframe(daily.set_index('date'), height=300)
