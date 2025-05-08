#results.py

# results.py

import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
from fpdf import FPDF
import altair as alt


def show_results():
    """
    Display simulation outcomes stored in session_state with key 'sim_out' and 'session_state'.
    Generates take-home messages and downloadable report.
    """
    # Retrieve simulation results from session state
    sim_out = st.session_state.get('sim_out')
    if sim_out is None:
        st.error("No simulation results found. Please run the simulation first.")
        return

    daily = sim_out['daily']
    summary = sim_out['summary']
    area = st.session_state.get('area', 1.0)
    cycle_days = st.session_state.get('cycle_days', len(daily) - 1)
    sow_date = pd.to_datetime(st.session_state.get('sowing_date'))

    # 1. Field-level Grain Yield
    grain_g_m2 = summary['grain_yield_est']  # g/m2
    grain_kg_ha = grain_g_m2 * 10            # convert to kg/ha
    total_grain_ton = grain_kg_ha * area/1000 #convert to ton

    st.title("Results summary")
    st.metric(label="Estimated Grain Yield (kg/ha)", value=f"{grain_kg_ha:.0f}")
    st.metric(label="Total Grain Yield (ton)", value=f"{total_grain_ton:.2f}")

    # 2. Phenological Milestones
    st.subheader("Phenological Milestones")
    df = daily.copy()
    day0 = df['date'].iloc[0]
    emergence_date = df.loc[df['TT'] >= 50, 'date'].min()
    flowering_date = df.loc[df['TT'] >= 600, 'date'].min()
    maturity_date = day0 + timedelta(days=cycle_days)

    col1, col2, col3 = st.columns(3)
    col1.metric("Days to Emergence", f"{(emergence_date - day0).days}")
    col2.metric("Days to Flowering", f"{(flowering_date - day0).days if pd.notna(flowering_date) else 'N/A'}")
    col3.metric("Days to Maturity", f"{(maturity_date - day0).days}")

    # 3. Stress Summary
    st.subheader("🧭 Stress Summary")
    swc = df['SWC']
    nmin = df['Nmin_total']
    w_thresh = swc.quantile(0.25)
    n_thresh = nmin.quantile(0.25)
    w_stress = swc <= w_thresh
    n_stress = nmin <= n_thresh
    pct_w = w_stress.mean() * 100
    pct_n = n_stress.mean() * 100

    st.write(f"**Water Stress:** {pct_w:.1f}% of days (SWC <= {w_thresh:.1f} mm)")
    st.write(f"**Nitrogen Stress:** {pct_n:.1f}% of days (Nmin <= {n_thresh:.1f} kg/ha)")

    # Add stress flags for plotting
    df['w_stress'] = w_stress
    df['n_stress'] = n_stress

    # Altair Water Stress Plot
    st.altair_chart(
        alt.layer(
            alt.Chart(df).mark_line(color='steelblue').encode(
                x='date:T', y=alt.Y('SWC:Q', title='Soil Water Content (mm)')
            ),
            alt.Chart(df).mark_area(opacity=0.3, color='red').encode(
                x='date:T',
                y='SWC:Q',
                y2=alt.Y2Value(0),
                opacity=alt.condition('datum.w_stress', alt.value(0.3), alt.value(0))
            )
        ).properties(height=260, title="Water Stress Over Time"),
        use_container_width=True
    )

    # Altair Nitrogen Stress Plot
    st.altair_chart(
        alt.layer(
            alt.Chart(df).mark_line(color='green').encode(
                x='date:T', y=alt.Y('Nmin_total:Q', title='Mineral N (kg/ha)')
            ),
            alt.Chart(df).mark_area(opacity=0.3, color='orange').encode(
                x='date:T',
                y='Nmin_total:Q',
                y2=alt.Y2Value(0),
                opacity=alt.condition('datum.n_stress', alt.value(0.3), alt.value(0))
            )
        ).properties(height=260, title="Nitrogen Stress Over Time"),
        use_container_width=True
    )

    # 4. Agronomic Recommendations
    st.subheader("🌾 Agronomic Recommendations")
    recs = []
    if any(n_stress):
        first_n = df.loc[n_stress, 'date'].iloc[0]
        recs.append(f"Severe nitrogen deficiency observed after {first_n.date()} - consider split fertilisation.")
    if pd.notna(flowering_date):
        window = (df['date'] >= flowering_date) & (df['date'] <= flowering_date + timedelta(days=10))
        if w_stress[window].mean() > 0.3:
            recs.append("Water stress peaked during flowering - expect yield penalties.")
    if not recs:
        recs.append("No critical stresses detected. Agronomic practices are appropriate.")
    for r in recs:
        st.write(f"- {r}")

    # 5. Downloadable PDF report
    st.subheader("🗃️ Download Report")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, 'Simulation Report', ln=True)
    pdf.set_font("Arial", size=12)
    pdf.ln(5)
    pdf.cell(0, 8, f"Field Area: {area} ha", ln=True)
    pdf.cell(0, 8, f"Yield: {grain_kg_ha:.0f} kg/ha, Total: {total_grain_ton:.2f} tons", ln=True)
    pdf.ln(5)
    pdf.cell(0, 8, 'Phenology:', ln=True)
    pdf.cell(0, 6, f"Emergence: {(emergence_date-day0).days} d", ln=True)
    pdf.cell(0, 6, f"Flowering: {(flowering_date-day0).days if pd.notna(flowering_date) else 'N/A'} d", ln=True)
    pdf.cell(0, 6, f"Maturity: {(maturity_date-day0).days} d", ln=True)
    pdf.ln(5)
    pdf.cell(0, 8, 'Stress Summary:', ln=True)
    pdf.cell(0, 6, f"Water Stress: {pct_w:.1f}% days", ln=True)
    pdf.cell(0, 6, f"Nitrogen Stress: {pct_n:.1f}% days", ln=True)
    pdf.ln(5)
    pdf.cell(0, 8, 'Recommendations:', ln=True)
    for r in recs:
        pdf.multi_cell(0, 6, f"- {r}")

    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    st.download_button(
        label="Download PDF Report",
        data=pdf_bytes,
        file_name="simulation_report.pdf",
        mime="application/pdf"
    )
