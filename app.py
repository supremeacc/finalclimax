import streamlit as st

from components.sidebar import render_sidebar
from components.heatmap_panel import render_heatmap_panel
from components.timeseries_panel import render_timeseries_panel
from components.comparison_panel import render_comparison_panel
from components.story_panel import render_story_panel
from components.insights_panel import render_insights_panel
from modules.visualizations import generate_climate_animation, generate_3d_globe

# ── Page Config ──
st.set_page_config(
    page_title="ClimaScope",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Dark‑Theme Custom CSS ──
st.markdown("""
<style>
    /* ---- Global overrides ---- */
    [data-testid="stAppViewContainer"] {
        background-color: #0e1117;
    }
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #21262d;
        min-width: 280px !important;
        max-width: 280px !important;
    }
    [data-testid="stSidebar"] h3 {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #8b949e;
        margin-bottom: 0.4rem;
    }
    /* Section card wrapper */
    .section-card {
        background: #161b22;
        border: 1px solid #21262d;
        border-radius: 12px;
        padding: 1.5rem 1.8rem;
        margin-bottom: 1.6rem;
    }
    /* Title styling */
    .hero-title {
        text-align: center;
        padding: 0.8rem 0 0.4rem;
    }
    .hero-title h1 {
        font-size: 2.2rem;
        font-weight: 700;
        color: #e6edf3;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .hero-title p.subtitle {
        font-size: 1.05rem;
        color: #8b949e;
        margin: 0.25rem 0 0;
        font-weight: 400;
    }
    /* Section headers */
    .section-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: #e6edf3;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .section-header .icon {
        font-size: 1.4rem;
    }
    /* Subtle dividers */
    hr {
        border: none;
        border-top: 1px solid #21262d;
        margin: 1.5rem 0;
    }
    /* Tab styling tweaks */
    [data-testid="stTabs"] button {
        color: #8b949e !important;
        font-weight: 500;
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        color: #00d2ff !important;
        border-bottom-color: #00d2ff !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Hero Header ──
st.markdown("""
<div class="hero-title">
    <h1>ClimaScope</h1>
    <p class="subtitle">Global Climate Data Explorer</p>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# ── Session State ──
if 'dataset' not in st.session_state:
    st.session_state.dataset = None

# ── Sidebar Controls ──
selected_var, selected_time, lat, lon = render_sidebar()

# ── Main Content ──
if st.session_state.dataset is not None and selected_var is not None:
    ds = st.session_state.dataset

    # ── Global Climate Map ──
    with st.container():
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">🌍 Global Climate Map</div>', unsafe_allow_html=True)
        st.caption("Spatial distribution of the selected climate variable.")
        viz_mode = st.radio(
            "Visualization Mode",
            ["Map View", "Globe View"],
            horizontal=True,
            key="viz_mode_toggle",
        )
        if viz_mode == "Map View":
            render_heatmap_panel(ds, selected_var, selected_time, lat=lat, lon=lon)
        else:
            with st.spinner("Rendering globe…"):
                fig_globe = generate_3d_globe(ds, selected_var, time_index=selected_time)
                if fig_globe:
                    st.plotly_chart(fig_globe, use_container_width=True, config={"displaylogo": False, "scrollZoom": True, "responsive": True})
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Summary Statistics ──
    with st.container():
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        render_insights_panel(ds, selected_var)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Location Time Trend ──
    with st.container():
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        render_timeseries_panel(ds, selected_var, lat, lon)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Climate Change Comparison ──
    with st.container():
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        render_comparison_panel(ds, selected_var)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Temporal Animation ──
    with st.container():
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">▶ Temporal Animation</div>', unsafe_allow_html=True)
        st.caption("Animated playback of the dataset over time.")
        if st.button("Generate Animation", key="anim_btn"):
            with st.spinner("Generating frames…"):
                fig_anim = generate_climate_animation(ds, selected_var)
                if fig_anim:
                    st.plotly_chart(fig_anim, use_container_width=True, config={"displaylogo": False, "scrollZoom": True, "responsive": True})
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Climate Insights ──
    with st.container():
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        render_story_panel(ds, selected_var, lat, lon)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # Empty state
    st.markdown("""
    <div style="text-align: center; padding: 6rem 2rem;">
        <h3 style="color: #8b949e; font-weight: 400;">No dataset loaded</h3>
        <p style="color: #484f58;">Upload a <code>.nc</code> file in the sidebar to begin.</p>
    </div>
    """, unsafe_allow_html=True)
