import streamlit as st
import pandas as pd
from modules.visualizations import generate_heatmap, generate_difference_heatmap
from modules.data_loader import get_time_range

def render_comparison_panel(ds, selected_var):
    """Renders the comparison feature to analyze differences between two time periods."""
    st.markdown('<div class="section-header">⚖ Climate Change Comparison</div>', unsafe_allow_html=True)
    times = get_time_range(ds)
    if times is None or len(times) == 0:
        st.warning("Dataset does not have a time dimension for comparison.")
        return
        
    # Time Selectors
    try:
        formatted_times = pd.to_datetime(times).strftime('%Y-%m-%d %H:%M:%S').tolist()
        
        times_list = times.tolist() if hasattr(times, 'tolist') else list(times)
        def format_func(x):
            return formatted_times[times_list.index(x)]
            
        col1, col2 = st.columns(2)
        with col1:
            time1 = st.selectbox("Baseline (T1)", options=times_list, index=0, format_func=format_func)
        with col2:
            time2 = st.selectbox("Comparison (T2)", options=times_list, index=len(times_list)-1, format_func=format_func)
    except Exception:
        times_list = times.tolist() if hasattr(times, 'tolist') else list(times)
        col1, col2 = st.columns(2)
        with col1:
            time1 = st.selectbox("Baseline (T1)", options=times_list, index=0)
        with col2:
            time2 = st.selectbox("Comparison (T2)", options=times_list, index=len(times_list)-1)
            
    if st.button("Compare", key="compare_btn"):
        with st.spinner("Generating comparison…"):
            map1, map2 = st.columns(2)
            
            with map1:
                st.subheader("Baseline (T1)")
                fig1 = generate_heatmap(ds, selected_var, time_index=time1)
                if fig1:
                    st.plotly_chart(fig1, use_container_width=True, key="compare_fig1", config={"displaylogo": False, "scrollZoom": True, "responsive": True})
                    
            with map2:
                st.subheader("Comparison (T2)")
                fig2 = generate_heatmap(ds, selected_var, time_index=time2)
                if fig2:
                    st.plotly_chart(fig2, use_container_width=True, key="compare_fig2", config={"displaylogo": False, "scrollZoom": True, "responsive": True})
                    
            st.divider()
            
            st.subheader("Difference (T2 − T1)")
            fig_diff = generate_difference_heatmap(ds, selected_var, time1, time2)
            if fig_diff:
                st.plotly_chart(fig_diff, use_container_width=True, key="compare_fig_diff", config={"displaylogo": False, "scrollZoom": True, "responsive": True})
