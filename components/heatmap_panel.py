import streamlit as st
from modules.visualizations import generate_heatmap

def render_heatmap_panel(ds, selected_var, selected_time, lat=None, lon=None):
    """Renders the central heatmap visualization."""
    st.markdown('<div class="section-header">Global Spatial Distribution</div>', unsafe_allow_html=True)
    with st.spinner("Generating 2D heatmap..."):
        fig_map = generate_heatmap(ds, selected_var, time_index=selected_time, selected_lat=lat, selected_lon=lon)
        if fig_map:
            # Render chart and capture click events natively
            event = st.plotly_chart(
                fig_map, 
                use_container_width=True, 
                config={"displaylogo": False, "scrollZoom": True, "responsive": True},
                on_select="rerun", 
                selection_mode="points"
            )
            
            # Intercept geographic point clicks
            if event and "selection" in event and "points" in event["selection"] and event["selection"]["points"]:
                pt = event["selection"]["points"][0]
                if "lat" in pt and "lon" in pt:
                    new_lat = float(pt["lat"])
                    new_lon = float(pt["lon"])
                    
                    # Update session state & auto-sync inputs if coordinates changed
                    if st.session_state.get('selected_lat') != new_lat or st.session_state.get('selected_lon') != new_lon:
                        st.session_state.selected_lat = new_lat
                        st.session_state.selected_lon = new_lon
                        st.rerun()
                        
            st.caption("Click on the map to update the selected location.")
