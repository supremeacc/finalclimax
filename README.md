# ClimaScope

**Global Climate Data Explorer**

ClimaScope is an interactive dashboard for exploring NetCDF climate datasets. Upload any `.nc` file and instantly visualize spatial distributions, temporal trends, and climate anomalies — no coding required.

---

## Features

### Global Climate Map
Spatial heatmap of any climate variable rendered on a Natural Earth projection with coastlines, country borders, and smooth color interpolation. Supports two visualization modes:
- **Map View** — flat geographic heatmap with click-to-select location
- **Globe View** — interactive 3D orthographic globe with dense interpolated rendering and Turbo colorscale

### Location Time Trend
Time-series analysis at any geographic point. Select a location by clicking the map or entering coordinates in the sidebar. Includes automatic resampling and trend smoothing.

### Climate Change Comparison
Side-by-side comparison of two time periods with a Gaussian-smoothed difference map. Red indicates increase, blue indicates decrease.

### Summary Statistics
Global summary metrics computed from the full dataset:
- Global average, maximum, and minimum values with locations
- Largest step change between consecutive time steps

### Climate Insights
Three analysis views consolidated into expandable sections:
- **Global Snapshot** — baseline spatial distribution at the earliest time step
- **Climate Change Comparison** — anomaly map between earliest and latest time steps
- **Time Trend** — temporal evolution at the selected location

### Temporal Animation
Animated playback of the dataset across the full time dimension with consistent color scaling across frames.

### Adaptive Dataset Handling
Automatically detects variable types and units from metadata, applies conversions (K → °C, Pa → hPa), and selects appropriate color scales.

---

## Project Structure

```
PyClimaExplorer/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── components/
│   ├── sidebar.py                  # Dataset upload, variable/time/location controls
│   ├── heatmap_panel.py            # Global spatial heatmap with click-to-select
│   ├── timeseries_panel.py         # Location time-series chart
│   ├── comparison_panel.py         # Side-by-side time period comparison
│   ├── insights_panel.py           # Summary statistics panel
│   └── story_panel.py              # Multi-view climate insights
├── modules/
│   ├── data_loader.py              # NetCDF loading and coordinate detection
│   ├── variable_adapter.py         # Unit conversion and color scale mapping
│   ├── analysis.py                 # Statistical computations
│   └── visualizations.py           # All Plotly chart/globe/animation generators
└── data/                           # Local .nc files auto-loaded on startup
```

---

## Technologies

| Technology | Purpose |
|---|---|
| Python | Core language |
| Streamlit | Dashboard framework |
| Xarray | NetCDF data handling |
| NumPy | Numerical operations |
| Plotly | Interactive visualizations and 3D globe |
| SciPy | Gaussian smoothing and interpolation |
| Pandas | Time-series formatting |

---

## Supported Datasets

**Format:** NetCDF (`.nc`) with standard coordinate dimensions (`time`, `lat`/`latitude`, `lon`/`longitude`).

Commonly tested variables:
- Temperature — `air`, `sst`, `t2m`
- Sea Level Pressure — `slp`, `msl`, `prmsl`
- Wind Speed — `uwnd`, `vwnd`, `u10`, `v10`
- Precipitation — `precip`, `pr`, `tp`

**Public test datasets:**
- [NOAA/NCEP Reanalysis](https://psl.noaa.gov/data/gridded/data.ncep.reanalysis.html)
- [NASA GISS Surface Temperature](https://data.giss.nasa.gov/gistemp/)
- [NCEP/DOE Reanalysis 2](https://psl.noaa.gov/data/gridded/data.ncep.reanalysis2.html)

---

## Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

The dashboard opens at `http://localhost:8501`.

---

## Usage

1. Upload a `.nc` file via the sidebar or place files in the `data/` folder.
2. Select a variable and time step.
3. Switch between Map View and Globe View for spatial exploration.
4. Click the map or enter coordinates to analyze temporal trends.
5. Use the comparison panel to detect anomalies between time periods.

---

## Future Work

- Multi-variable overlay analysis
- Predictive climate modeling
- Anomaly detection and alerting
