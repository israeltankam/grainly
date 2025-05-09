#results.py

import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
from fpdf import FPDF
import altair as alt


def show_results():
    """
    Display simulation outcomes stored in session_state with key 'sim_out'.
    Calculates water and nitrogen stress indices and provides recommendations.
    """
    sim_out = st.session_state.get('sim_out')
    if sim_out is None:
        st.error("No simulation results found. Please run the simulation first.")
        return

    df = sim_out['daily'].copy()
    summary = sim_out['summary']
    area = st.session_state.get('area', 1.0)
    cycle_days = st.session_state.get('cycle_days', len(df) - 1)
    sow_date = pd.to_datetime(st.session_state.get('sowing_date'))

    # 1. Yield Metrics
    grain_g_m2 = summary['grain_yield_est']
    grain_kg_ha = grain_g_m2 * 10
    total_grain_ton = grain_kg_ha * area / 1000

    st.title("Results Summary")
    st.metric("Estimated Grain Yield (kg/ha)", f"{grain_kg_ha:.0f}")
    st.metric("Total Grain Yield (ton)", f"{total_grain_ton:.2f}")

    # 2. Phenology
    st.subheader("Phenological Milestones")
    day0 = df['date'].iloc[0]
    emergence = df.loc[df['TT'] >= 50, 'date'].min()
    flowering = df.loc[df['TT'] >= 600, 'date'].min()
    maturity = day0 + timedelta(days=cycle_days)
    c1, c2, c3 = st.columns(3)
    c1.metric("Days to Emergence", f"{(emergence - day0).days}")
    c2.metric("Days to Flowering", f"{(flowering - day0).days if pd.notna(flowering) else 'N/A'}")
    c3.metric("Days to Maturity", f"{(maturity - day0).days}")

    # 3. Stress Calculations
    st.subheader("🧭 Stress Summary")
    # Water stress via Relative Extractable Water (REW)
    WP = df['SWC'].min()
    FC = df['SWC'].max()
    df['REW'] = (df['SWC'] - WP) / (FC - WP + 1e-6)
    thresh = 0.5
    df['water_stress'] = df['REW'].apply(lambda x: max(0, 1 - x/thresh) if x < thresh else 0)
    mean_ws = df['water_stress'].mean() * 100

    # Nitrogen stress via daily demand
    df['dB'] = df['Biomass'].diff().fillna(df['Biomass'])
    df['N_demand'] = df['dB'] * 10 * 0.03
    # ensure positive demand
    demand_mean = df['N_demand'][df['N_demand'] > 0].mean() if (df['N_demand'] > 0).any() else 1.0
    df['N_demand'] = df['N_demand'].replace(0, demand_mean)
    df['nitrogen_stress'] = df.apply(
        lambda r: max(0, 1 - min(r['Nmin_total'], r['N_demand'])/r['N_demand']),
        axis=1
    )
    mean_ns = df['nitrogen_stress'].mean() * 100

    st.write(f"**Mean Water Stress:** {mean_ws:.1f}%")
    st.write(f"**Mean Nitrogen Stress:** {mean_ns:.1f}%")

    # Plot stress
    ws_chart = alt.Chart(df).mark_line(color='blue').encode(
        x='date:T', y=alt.Y('water_stress:Q', title='Water Stress'),
        tooltip=['date:T','water_stress:Q']
    ).properties(height=220, title='Daily Water Stress')
    ns_chart = alt.Chart(df).mark_line(color='brown').encode(
        x='date:T', y=alt.Y('nitrogen_stress:Q', title='Nitrogen Stress'),
        tooltip=['date:T','nitrogen_stress:Q']
    ).properties(height=220, title='Daily Nitrogen Stress')
    st.altair_chart(ws_chart, use_container_width=True)
    st.altair_chart(ns_chart, use_container_width=True)

    # 4. Agronomic Recommendations
    st.subheader("🌾 Agronomic Recommendations")
    recs = []
    # Urgent fertilization if initial N very low
    initial_n = st.session_state.get('initial_nitrate', 0.0)
    if initial_n < 20:
        recs.append("Initial soil N is critically low (<20 kg/ha) - consider urgent fertilization before sowing.")
    # Seasonal stress warnings
    if mean_ws > 30:
        recs.append("High average water stress - adjust irrigation schedule.")
    if mean_ns > 30:
        recs.append("High average N stress - plan split N applications.")
    if not recs:
        recs.append("No critical stresses detected. Management is adequate.")
    for r in recs:
        st.write(f"- {r}")

    # 5. Download PDF report
    st.subheader("🗃️ Download Report")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, 'Simulation Report', ln=True)
    pdf.set_font("Arial", size=12)
    pdf.ln(5)
    pdf.cell(0, 8, f"Field Area: {area} ha", ln=True)
    pdf.cell(0, 8, f"Yield: {grain_kg_ha:.0f} kg/ha ({total_grain_ton:.2f} t)", ln=True)
    pdf.ln(5)
    pdf.cell(0, 8, f"Mean Water Stress: {mean_ws:.1f}%", ln=True)
    pdf.cell(0, 8, f"Mean Nitrogen Stress: {mean_ns:.1f}%", ln=True)
    pdf.ln(5)
    pdf.cell(0, 8, 'Recommendations:', ln=True)
    for r in recs:
        pdf.multi_cell(0, 6, f"- {r}")

    data = pdf.output(dest='S').encode('latin-1', 'replace')
    st.download_button("Download PDF Report", data=data, file_name="simulation_report.pdf", mime="application/pdf")
