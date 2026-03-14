import streamlit as st
import pandas as pd
from modules.visualizations import generate_heatmap, generate_difference_heatmap, generate_time_series
from modules.data_loader import get_time_range

def render_story_panel(ds, selected_var, lat, lon):
    """
    Renders three analysis blocks: Global Snapshot, Climate Anomaly, and Location Trend.
    """
    st.markdown('<div class="section-header">🔍 Climate Insights</div>', unsafe_allow_html=True)
    st.caption("Spatial, temporal, and anomaly analysis of the loaded dataset.")
    
    times = get_time_range(ds)
    has_time = times is not None and len(times) > 0
    
    # ── Global Snapshot ──
    with st.expander("Global Snapshot", expanded=True):
        if has_time:
            first_time = times[0]
            try:
                label = pd.to_datetime(first_time).strftime('%Y-%m-%d')
            except:
                label = str(first_time)
            st.caption(f"Baseline spatial distribution at {label}.")
            fig = generate_heatmap(ds, selected_var, time_index=first_time, selected_lat=lat, selected_lon=lon)
        else:
            fig = generate_heatmap(ds, selected_var, selected_lat=lat, selected_lon=lon)
            
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="story_fig1", config={"displaylogo": False, "scrollZoom": True, "responsive": True})
    
    # ── Climate Change Comparison ──
    with st.expander("Climate Change Comparison", expanded=False):
        if not has_time or len(times) < 2:
            st.warning("At least two time steps are required for anomaly analysis.")
        else:
            first_time = times[0]
            last_time = times[-1]
            
            try:
                t1_label = pd.to_datetime(first_time).strftime('%Y-%m-%d')
                t2_label = pd.to_datetime(last_time).strftime('%Y-%m-%d')
            except:
                t1_label = str(first_time)
                t2_label = str(last_time)
            
            st.caption(f"Difference between {t2_label} and {t1_label}. Red indicates increase, blue indicates decrease.")
            
            fig_diff = generate_difference_heatmap(ds, selected_var, first_time, last_time)
            if fig_diff:
                st.plotly_chart(fig_diff, use_container_width=True, key="story_fig2", config={"displaylogo": False, "scrollZoom": True, "responsive": True})
    
    # ── Time Trend ──
    with st.expander("Time Trend", expanded=False):
        if not has_time:
            st.warning("No time dimension available for trend analysis.")
        else:
            if lat is not None and lon is not None:
                st.caption(f"Temporal trend at Lat {lat:.2f}, Lon {lon:.2f}. Adjust coordinates in the sidebar.")
                fig_ts = generate_time_series(ds, selected_var, lat, lon)
                if fig_ts:
                    st.plotly_chart(fig_ts, use_container_width=True, key="story_fig3", config={"displaylogo": False, "scrollZoom": True, "responsive": True})
            else:
                st.warning("Set latitude and longitude in the sidebar to view the time trend.")
