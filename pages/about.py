# about.py

import streamlit as st

def about():
    st.markdown("""
    # 🌽 About Grainly, a Maize Growth Simulator
    
    **Welcome to a new-generation tool for precision agriculture!** This app helps farmers and agronomists optimize maize production through scientific simulations powered by the STICS crop model.

    ## 🚀 Key Features
    
    ### 🌍 Smart Field Configuration
    - Geolocation mapping with weather integration
    - 12 soil type profiles with auto-calculated properties
    - Customizable fertilization & irrigation schedules 📅
    - Variety database with 5 maize cultivars 🌱

    ### 📈 Advanced Simulation Engine
    - STICS-model inspired calculations
    - Daily thermal time accumulation 🌡️
    - Leaf Area Index (LAI) development
    - Biomass growth with light-use efficiency
    - Water & nitrogen stress detection ⚠️

    ### 📊 Dynamic Results Dashboard
    - Interactive growth charts
    - Phenological stage tracking 🌱➡️🌽
    - Stress period identification
    - Yield estimation with field-size scaling
    - Automatic PDF report generation 📄

    ## 🔧 How It Works
    1. **Setup** your field parameters and management practices
    2. **Simulate** crop development with historical+forecast weather data 🌤️
    3. **Analyze** results with interactive visualizations
    4. **Optimize** practices based on data-driven recommendations

    ## 🌐 Data Sources
    - **Weather Data**: Open-Meteo API (historical + forecast)
    - **Soil Properties**: FAO Soil Grids parameters
    - **Crop Varieties**: CIMMYT maize database 📚
    - **Agronomic Models**: STICS model adaptations

    ## ⚙️ Technology Stack
    - **Frontend**: Streamlit + Hydralit Components
    - **Visualization**: Altair + Matplotlib
    - **Geospatial**: Geopy
    - **Data Processing**: Pandas + NumPy
    - **Reporting**: FPDF + Template design

    ## ⚠️ Disclaimer
    > While we use scientific models, actual field results may vary due to:
    > - Microclimate variations 🏞️
    > - Unpredictable weather events 🌪️
    > - Soil heterogeneity
    > - Pest/disease pressures 🐛
    > 
    > Always validate with field observations!

    ✉️ **Contact Support**: [israeltankam@gmail.com](israeltankam@gmail.com) 

    Version 1.1 | Updated: May 2025 | 
    """, unsafe_allow_html=True)
    

    st.caption("""
    🚧 Note: Current version (1.1) focuses on maize baseline modelling
    
    🧾 Custom crop disease modelling available upon request -- subject to consultation and provision of data. 
    
    © Enterely designed and developed by Israël Tankam ! All rights reserved
    """)