#!/usr/bin/env python
# coding: utf-8

# In[ ]:

#app.py

import streamlit as st
import hydralit_components as hc
from pages.main.get_start import setup_page
from pages.main.simulation import run_simulation_page
from pages.main.results import show_results
from pages.about import about


# Set page layout to centered and responsive
# st.set_page_config(layout="wide")
st.set_page_config(layout='wide',initial_sidebar_state='collapsed')

# specify the primary menu definition
menu_data = [
    {'icon': "fa fa-desktop", 'label':"Setup"},
    {'icon': "fas fa-chart-area", 'label':"Simulation"},
    {'icon': "fa fa-calculator", 'label':"Results"},
    {'icon': "fa fa-book", 'label':"About"},
]

over_theme = {'txc_inactive': '#FFFFFF', 'menu_background':'#bac96b'}
logo_path = "src/images/logo/logo.png"
st.image(logo_path, width=164)
main_tab= hc.nav_bar(
    menu_definition=menu_data,
    override_theme=over_theme,
    hide_streamlit_markers=False, #will show the st hamburger as well as the navbar now!
    sticky_nav=True, #at the top or not
    sticky_mode='pinned', #jumpy or not-jumpy, but sticky or pinned
)


def dummy():
    st.markdown("## Under construction")
    
# Page router
if main_tab == "Setup":
    setup_page()  
if main_tab == "About":
    about()
elif main_tab == "Simulation":
    run_simulation_page() 
elif main_tab == "Results":
    show_results()