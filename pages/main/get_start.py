# get_start.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from functools import lru_cache
import time
import warnings
warnings.filterwarnings('ignore')

# Define soil properties for texture classes
_SOIL_TABLE = {
    'sand':                {'field_capacity': 0.10, 'wilting_point': 0.03},
    'loamy sand':          {'field_capacity': 0.13, 'wilting_point': 0.05},
    'sandy loam':          {'field_capacity': 0.18, 'wilting_point': 0.07},
    'loam':                {'field_capacity': 0.27, 'wilting_point': 0.11},
    'silt loam':           {'field_capacity': 0.36, 'wilting_point': 0.20},
    'silt':                {'field_capacity': 0.45, 'wilting_point': 0.30},
    'sandy clay loam':     {'field_capacity': 0.20, 'wilting_point': 0.10},
    'clay loam':           {'field_capacity': 0.35, 'wilting_point': 0.18},
    'silty clay loam':     {'field_capacity': 0.38, 'wilting_point': 0.23},
    'sandy clay':          {'field_capacity': 0.23, 'wilting_point': 0.13},
    'silty clay':          {'field_capacity': 0.41, 'wilting_point': 0.26},
    'clay':                {'field_capacity': 0.47, 'wilting_point': 0.27}
}

# Cached geocoding functions
@lru_cache(maxsize=100)
def cached_geocode(query, limit=5):
    """Cached geocoding function with proper user agent"""
    geolocator = Nominatim(user_agent="stics_app (contact@example.com)")
    try:
        return geolocator.geocode(query, exactly_one=False, limit=limit)
    except (GeocoderTimedOut, GeocoderServiceError):
        return []
    except Exception:
        return []

@lru_cache(maxsize=100)
def cached_geocode_single(query):
    """Cached geocoding for single location"""
    geolocator = Nominatim(user_agent="stics_app (contact@example.com)")
    try:
        return geolocator.geocode(query, exactly_one=True, timeout=10)
    except Exception:
        return None

# Helper: load variety list from CSV
def load_varieties(csv_path="src/data/maize_varieties.csv"):
    df = pd.read_csv(csv_path, encoding='ISO-8859-1')
    return df['Variety'].tolist()

# Callbacks to sync widget values into session state
def callback_factory(key):
    def _callback():
        st.session_state[key] = st.session_state[f"widget_{key}"]
    return _callback

# Initialize session state defaults
def init_session_state():
    st.session_state.setdefault('area', 1.0)
    st.session_state.setdefault('density', 7.0)
    st.session_state.setdefault('sowing_date', date.today())
    st.session_state.setdefault('sowing_depth', 5)
    st.session_state.setdefault('initial_nitrate', 70.0)
    
    # Initialize schedules
    sow = st.session_state['sowing_date']
    dates = [sow + timedelta(days=30*i) for i in range(4)]
    if 'fert_schedule' not in st.session_state:
        st.session_state['fert_schedule'] = pd.DataFrame({'date': dates, 'amount': [50]*4})
    if 'irr_schedule' not in st.session_state:
        st.session_state['irr_schedule'] = pd.DataFrame({'date': dates, 'amount': [20]*4})
    
    # Location defaults
    location_defaults = {
        'location': '', 
        'raw_location': '', 
        'location_suggestions': [],
        'last_geocode_time': 0
    }
    for k, v in location_defaults.items():
        st.session_state.setdefault(k, v)
    
    # Soil and variety defaults
    defaults = {
        'variety': 'Resolute', 
        'use_expert_soil': False, 
        'soil_type': 'loam',
        'soil_layers': pd.DataFrame([
            {'depth_top': 0.0, 'depth_bottom': 0.3, 'texture': 'loam',
             'field_capacity': _SOIL_TABLE['loam']['field_capacity'],
             'wilting_point': _SOIL_TABLE['loam']['wilting_point']}
        ])
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    
    # Sync widget states
    for k in ['raw_location','variety','area','density','sowing_date','sowing_depth','initial_nitrate','use_expert_soil','soil_type']:
        widget = f"widget_{k}"
        st.session_state.setdefault(widget, st.session_state[k])

# Main setup page
def setup_page():
    init_session_state()
    col1, _ = st.columns([3,4])
    with col1:
        st.subheader("Setup")

        # Location section with search button
        st.text_input(
            "Field location (City, Country)",
            key='widget_raw_location',
            value=st.session_state['raw_location'],
            on_change=callback_factory('raw_location'),
            help="Type your field location and click 'Search Locations'"
        )
        
        # Search button triggers geocoding
        if st.button("Search Locations", key="search_btn"):
            query = st.session_state['raw_location']
            if query:
                # Rate limiting
                now = time.time()
                elapsed = now - st.session_state.last_geocode_time
                if elapsed < 1.2:  # 1.2 seconds between requests
                    time.sleep(1.2 - elapsed)
                
                with st.spinner("Searching locations..."):
                    try:
                        results = cached_geocode(query, limit=5)
                        if results:
                            st.session_state['location_suggestions'] = [r.address for r in results]
                        else:
                            st.session_state['location_suggestions'] = []
                            st.warning("No locations found. Try a different query.")
                    except Exception as e:
                        st.error(f"Geocoding error: {str(e)}")
                        st.session_state['location_suggestions'] = []
                
                st.session_state.last_geocode_time = time.time()
        
        # Location suggestions dropdown
        loc_opts = st.session_state['location_suggestions']
        if loc_opts:
            idx = loc_opts.index(st.session_state['location']) if st.session_state['location'] in loc_opts else 0
            selection = st.selectbox(
                "Select location",
                options=loc_opts,
                index=idx,
                key='widget_location',
                on_change=callback_factory('location')
            )
            
            # Get coordinates for selected location
            if selection and selection != st.session_state.get('last_selection'):
                try:
                    loc = cached_geocode_single(selection)
                    if loc:
                        st.session_state['location_coords'] = (loc.latitude, loc.longitude)
                        st.session_state['last_selection'] = selection
                    else:
                        st.warning("Could not get coordinates for this location")
                except Exception as e:
                    st.warning(f"Coordinate lookup failed: {str(e)}")

        # Crop
        st.subheader("Crop")
        varieties = load_varieties()
        idx_var = varieties.index(st.session_state['variety']) if st.session_state['variety'] in varieties else 0
        st.selectbox(
            "Maize variety",
            options=varieties,
            index=idx_var,
            key='widget_variety',
            on_change=callback_factory('variety')
        )
        
        # Field
        st.subheader("Field")
        st.number_input(
            "Field area (ha)", min_value=0.1, step=0.1,
            key='widget_area',
            value=st.session_state['area'],
            on_change=callback_factory('area')
        )
        
        # Planting
        st.subheader("Planting")
        st.number_input(
            "Planting density (plants/m²)", min_value=1.0, step=0.5,
            key='widget_density',
            value=st.session_state['density'],
            on_change=callback_factory('density')
        )
        
        st.date_input(
            "Sowing date",
            key='widget_sowing_date',
            value=st.session_state['sowing_date'],
            on_change=callback_factory('sowing_date')
        )
        
        st.number_input(
            "Sowing depth (cm)", min_value=1, step=1,
            key='widget_sowing_depth',
            value=st.session_state['sowing_depth'],
            on_change=callback_factory('sowing_depth')
        )

        # Soil Configuration
        st.subheader("Soil Configuration")
        expert = st.checkbox(
            "Enable expert soil layers",
            key='widget_use_expert_soil',
            value=st.session_state['use_expert_soil'],
            on_change=callback_factory('use_expert_soil'),
            help="Toggle to Expert mode: define custom soil profile layers"
        )
        
        if expert:
            soil_df = st.session_state['soil_layers']
            edited = st.data_editor(
                soil_df, num_rows="dynamic", key='soil_layers_editor'
            )
            st.session_state['soil_layers'] = edited
        else:
            display_soils = list(_SOIL_TABLE.keys())
            soil_choice_display = st.selectbox(
                "Soil type",
                options=display_soils,
                index=0,
                key='widget_soil_type',
                on_change=callback_factory('soil_type')
            )

        # Fertilization Schedule
        st.subheader("Fertilization Schedule")
        st.caption("Amounts in Kg/ha per event; add or remove rows as needed.")
        fert_df = st.data_editor(
            st.session_state['fert_schedule'],
            num_rows="dynamic",
            key='fert_schedule_editor'
        )
        st.session_state['fert_schedule'] = fert_df

        # Irrigation Schedule
        st.subheader("Irrigation Schedule")
        st.caption("Amounts in mm per event; add or remove rows as needed.")
        irr_df = st.data_editor(
            st.session_state['irr_schedule'],
            num_rows="dynamic",
            key='irr_schedule_editor'
        )
        st.session_state['irr_schedule'] = irr_df

        # Initial Soil Nitrogen
        st.subheader("Initial Soil Nitrogen")
        st.number_input(
            "Initial soil nitrate (kg N/ha)", min_value=0.0, step=5.0,
            key='widget_initial_nitrate',
            value=st.session_state['initial_nitrate'],
            on_change=callback_factory('initial_nitrate')
        )
        


    # For debugging session state (uncomment during development)
    # st.write(st.session_state)



