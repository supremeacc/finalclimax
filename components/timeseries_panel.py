import streamlit as st
from modules.visualizations import generate_time_series

@st.fragment
def render_timeseries_panel(ds, selected_var, lat, lon):
    """Renders the right visualization panel for time series analysis.
    Decorated with @st.fragment so lat/lon changes only rerun this panel,
    not the entire dashboard (map stays untouched).
    """
    st.markdown('<div class="section-header">📈 Location Time Trend</div>', unsafe_allow_html=True)
    
    # Read latest lat/lon from session state to pick up sidebar/map-click changes
    current_lat = st.session_state.get('selected_lat', lat)
    current_lon = st.session_state.get('selected_lon', lon)
    
    if current_lat is not None and current_lon is not None:
        fig_ts = generate_time_series(ds, selected_var, current_lat, current_lon)
        if fig_ts:
            st.plotly_chart(fig_ts, use_container_width=True, config={"displaylogo": False, "scrollZoom": True, "responsive": True})
    else:
        st.warning("Missing latitude/longitude coordinates.")

