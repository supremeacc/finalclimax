import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
import numpy as np
from modules.data_loader import get_spatial_slice, get_location_timeseries
from modules.variable_adapter import get_variable_info, normalize_values, compute_color_range

def _prepare_spatial_data(dataset, variable, time_index=None):
    """
    Helper function to extract, subset, and clean spatial data from xarray to pandas.
    Returns the DataFrame and the actual coordinate column names.
    """
    # Handle time slicing using optimized data_loader function
    data = get_spatial_slice(dataset, variable, time_index)
    if data is None:
        return None, None, None
            
    try:
        lat_dim = 'lat' if 'lat' in data.dims else 'latitude' if 'latitude' in data.dims else None
        lon_dim = 'lon' if 'lon' in data.dims else 'longitude' if 'longitude' in data.dims else None
        
        if lat_dim and lon_dim:
            # Downsample the dataset grid to improve map rendering performance
            data = data.isel({lat_dim: slice(None, None, 2), lon_dim: slice(None, None, 2)})
            
        df = data.to_dataframe().reset_index()
        lat_col = 'lat' if 'lat' in df.columns else 'latitude' if 'latitude' in df.columns else None
        lon_col = 'lon' if 'lon' in df.columns else 'longitude' if 'longitude' in df.columns else None
        
        if not lat_col or not lon_col:
            st.error("Dataset missing standard latitude or longitude coordinates ('lat'/'lon' or 'latitude'/'longitude').")
            return None, None, None
            
        df_clean = df.dropna(subset=[variable])
        return df_clean, lat_col, lon_col
    except Exception as e:
        st.error(f"Error extracting spatial data: {e}")
        return None, None, None

@st.cache_data(hash_funcs={"xarray.core.dataset.Dataset": id})
def _get_smoothed_spatial_df(dataset, variable, time_index):
    """Cached helper to slice, interpolate, smooth, and normalize spatial data."""
    data = get_spatial_slice(dataset, variable, time_index)
    if data is None:
        return None
        
    lat_dim = 'lat' if 'lat' in data.dims else 'latitude' if 'latitude' in data.dims else None
    lon_dim = 'lon' if 'lon' in data.dims else 'longitude' if 'longitude' in data.dims else None
    
    if lat_dim and lon_dim:
        # Convert longitude from 0-360 to -180 to 180
        if data[lon_dim].max() > 180:
            data.coords[lon_dim] = (data.coords[lon_dim] + 180) % 360 - 180
            data = data.sortby(lon_dim)
        
        # Downsample to a lighter grid for faster visualization rendering
        new_lats = np.linspace(float(data[lat_dim].min()), float(data[lat_dim].max()), 72)
        new_lons = np.linspace(float(data[lon_dim].min()), float(data[lon_dim].max()), 144)
        data = data.interp({lat_dim: new_lats, lon_dim: new_lons}, method='linear')
        
    data = data.transpose(lat_dim, lon_dim)
    
    lats = data[lat_dim].values
    lons = data[lon_dim].values
    z_values = data.values

    # Apply unit normalization (K→°C, Pa→hPa) for visualization only
    var_info = get_variable_info(dataset, variable)
    z_values = normalize_values(z_values, var_info)

    import scipy.ndimage as ndimage
    
    # Replace NaNs for smoothing
    z_mean = np.nanmean(z_values)
    z_filled = np.nan_to_num(z_values, nan=z_mean)
    
    # Apply Gaussian smoothing to blend data seamlessly
    z_smoothed = ndimage.gaussian_filter(z_filled, sigma=2.0)
    
    # Mask out original NaNs
    z_smoothed[np.isnan(z_values)] = np.nan
    
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    
    df = pd.DataFrame({
        'lon': lon_grid.flatten(),
        'lat': lat_grid.flatten(),
        'z': z_smoothed.flatten()
    }).dropna()
    
    return df

@st.cache_data(hash_funcs={"xarray.core.dataset.Dataset": id})
def _build_base_heatmap(dataset, variable, time_index=None):
    """
    Build the expensive base heatmap figure (scatter_geo) and cache it.
    Uses adaptive color scale and percentile-based range from variable_adapter.
    """
    try:
        df = _get_smoothed_spatial_df(dataset, variable, time_index)
        if df is None or df.empty:
            return None, None, None

        var_info = get_variable_info(dataset, variable)
        color_range, midpoint = compute_color_range(df['z'].values, var_info)
        units = var_info['display_units']
        units_label = f" ({units})" if units else ""
            
        fig = px.scatter_geo(
            df,
            lon='lon',
            lat='lat',
            color='z',
            projection="natural earth",
            color_continuous_scale=var_info['color_scale'],
            color_continuous_midpoint=midpoint,
            range_color=color_range
        )
        
        # High density square markers without borders to look like a fluid continuous map
        fig.update_traces(
            marker=dict(symbol='square', size=5, opacity=0.95, line=dict(width=0)),
            hovertemplate=f"Lat: %{{lat:.2f}}<br>Lon: %{{lon:.2f}}<br>Value: %{{marker.color:.2f}}{units_label}<extra></extra>"
        )

        fig.update_layout(
            title=f"Global Spatial Distribution: {variable}{units_label}",
            geo=dict(
                showcoastlines=True,
                coastlinecolor='white',
                showcountries=True,
                countrycolor='#484f58',
                bgcolor='#0e1117'
            ),
            uirevision='constant',
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            paper_bgcolor='#0e1117',
            plot_bgcolor='#0e1117'
        )
        
        return fig, df, var_info
    except Exception as e:
        st.error(f"Error building base heatmap: {e}")
        return None, None, None


def generate_heatmap(dataset, variable, time_index=None, selected_lat=None, selected_lon=None):
    """
    Generate a global heatmap with an optional location marker.
    The expensive base map is cached; only the lightweight marker overlay is recomputed.
    """
    result = _build_base_heatmap(dataset, variable, time_index)
    if result is None or result[0] is None:
        return None
    
    import copy
    fig = copy.deepcopy(result[0])
    df = result[1]
    var_info = result[2]
    units = var_info['display_units']
    units_label = f" {units}" if units else ""
    
    if selected_lat is not None and selected_lon is not None:
        adj_lon = (selected_lon + 180) % 360 - 180 if selected_lon > 180 else selected_lon
        
        # Find the nearest value for the tooltip
        dist = (df['lat'] - selected_lat)**2 + (df['lon'] - adj_lon)**2
        val_str = ""
        if not dist.empty:
            val = df.loc[dist.idxmin(), 'z']
            val_str = f"<br>Value: {val:.2f}{units_label}"
            
        # Crosshair Lines
        fig.add_trace(go.Scattergeo(
            lon=[-180, 180], lat=[selected_lat, selected_lat],
            mode='lines', line=dict(color='rgba(255, 255, 255, 0.5)', width=1, dash='dot'),
            hoverinfo='skip', showlegend=False
        ))
        fig.add_trace(go.Scattergeo(
            lon=[adj_lon, adj_lon], lat=[-90, 90],
            mode='lines', line=dict(color='rgba(255, 255, 255, 0.5)', width=1, dash='dot'),
            hoverinfo='skip', showlegend=False
        ))
        
        # Coordinates text overlay
        fig.add_trace(go.Scattergeo(
            lon=[adj_lon + 15 if adj_lon < 150 else adj_lon - 15],
            lat=[selected_lat + 10 if selected_lat < 70 else selected_lat - 10],
            mode='text',
            text=[f"Lat: {selected_lat:.1f}, Lon: {adj_lon:.1f}"],
            textfont=dict(color='white', size=12),
            hoverinfo='skip', showlegend=False
        ))
            
        fig.add_trace(go.Scattergeo(
            lon=[adj_lon],
            lat=[selected_lat],
            mode='markers',
            marker=dict(
                color='yellow',
                size=12,
                line=dict(color='black', width=2),
                symbol='circle'
            ),
            name='Selected Location',
            hovertemplate=f"Selected Location<br>Lat: {selected_lat:.2f}<br>Lon: {adj_lon:.2f}{val_str}<extra></extra>"
        ))
        
    return fig

def generate_3d_globe(dataset, variable, time_index=None):
    """
    Generate a dense, interactive 3D globe visualization of climate data.
    Uses Scattergeo with orthographic projection, interpolated grid for
    smooth visual density, and Turbo colorscale for scientific readability.

    Args:
        dataset (xr.Dataset): The climate dataset object.
        variable (str): The climate variable to plot.
        time_index (int or str, optional): The specific time slice to plot.

    Returns:
        go.Figure: The Plotly figure object.
    """
    if dataset is None or variable not in dataset:
        st.error(f"Variable '{variable}' not found in the dataset.")
        return None

    data = get_spatial_slice(dataset, variable, time_index)
    if data is None:
        return None

    lat_dim = 'lat' if 'lat' in data.dims else 'latitude' if 'latitude' in data.dims else None
    lon_dim = 'lon' if 'lon' in data.dims else 'longitude' if 'longitude' in data.dims else None

    if not lat_dim or not lon_dim:
        st.error("Dataset missing standard latitude or longitude coordinates.")
        return None

    try:
        # Convert longitude from 0–360 to –180..180 if needed
        if float(data[lon_dim].max()) > 180:
            data.coords[lon_dim] = (data.coords[lon_dim].values + 180) % 360 - 180
            data = data.sortby(lon_dim)

        # Interpolate to a denser grid for smooth visual coverage
        # Target ~90 lat × 180 lon for a good balance of density vs performance
        target_lat_n = min(90, len(data[lat_dim]))
        target_lon_n = min(180, len(data[lon_dim]))
        new_lats = np.linspace(float(data[lat_dim].min()), float(data[lat_dim].max()), target_lat_n)
        new_lons = np.linspace(float(data[lon_dim].min()), float(data[lon_dim].max()), target_lon_n)
        data = data.interp({lat_dim: new_lats, lon_dim: new_lons}, method='linear')

        # Apply light Gaussian smoothing to fill any remaining gaps
        import scipy.ndimage as ndimage
        z_values = data.values
        z_mean = np.nanmean(z_values)
        z_filled = np.nan_to_num(z_values, nan=z_mean)
        z_smoothed = ndimage.gaussian_filter(z_filled, sigma=1.0)
        z_smoothed[np.isnan(z_values)] = np.nan

        # Flatten to 1-D arrays
        lon_grid, lat_grid = np.meshgrid(new_lons, new_lats)
        lat_flat = lat_grid.flatten()
        lon_flat = lon_grid.flatten()
        values_flat = z_smoothed.flatten()

        # Remove NaNs
        valid = ~np.isnan(values_flat)
        lat_flat = lat_flat[valid]
        lon_flat = lon_flat[valid]
        values_flat = values_flat[valid]

        if len(values_flat) == 0:
            st.warning("No valid data points to display on the globe.")
            return None

        # Apply unit normalization (K→°C, Pa→hPa) for display
        var_info = get_variable_info(dataset, variable)
        values_flat = normalize_values(values_flat, var_info)
        units = var_info['display_units']
        units_label = f" ({units})" if units else ""

        # Compute adaptive color range from the data
        color_range, midpoint = compute_color_range(values_flat, var_info)

        # Build the dense Scattergeo trace
        fig = go.Figure()

        fig.add_trace(go.Scattergeo(
            lat=lat_flat,
            lon=lon_flat,
            mode="markers",
            marker=dict(
                size=6,
                color=values_flat,
                colorscale=var_info.get('color_scale', 'Turbo'),
                cmin=color_range[0],
                cmax=color_range[1],
                cmid=midpoint,
                opacity=0.9,
                colorbar=dict(
                    title=dict(
                        text=f"{variable}{units_label}",
                        font=dict(color='#c9d1d9', size=13),
                    ),
                    tickfont=dict(color='#8b949e', size=11),
                    bgcolor='rgba(22,27,34,0.85)',
                    bordercolor='#30363d',
                    borderwidth=1,
                    thickness=15,
                    len=0.55,
                    xpad=10,
                ),
                line=dict(width=0),
            ),
            hovertemplate=(
                f"Lat: %{{lat:.1f}}°<br>"
                f"Lon: %{{lon:.1f}}°<br>"
                f"{variable}: %{{marker.color:.2f}}{units_label}"
                f"<extra></extra>"
            ),
        ))

        # Orthographic globe layout — dark Earth so data colors pop
        fig.update_layout(
            title=dict(
                text=f"🌍 3D Climate Globe: {variable}{units_label}",
                font=dict(color='#e6edf3', size=17),
                x=0.5,
            ),
            geo=dict(
                projection_type="orthographic",
                showland=True,
                landcolor="rgb(35, 35, 35)",
                showocean=True,
                oceancolor="rgb(10, 15, 40)",
                showcountries=True,
                countrycolor="rgba(80, 80, 90, 0.6)",
                showcoastlines=True,
                coastlinecolor="rgba(120, 130, 140, 0.5)",
                showlakes=True,
                lakecolor="rgb(10, 15, 40)",
                bgcolor="rgba(0,0,0,0)",
                projection_rotation=dict(lon=0, lat=20),
            ),
            paper_bgcolor='#0e1117',
            plot_bgcolor='#0e1117',
            margin=dict(l=0, r=0, t=50, b=0),
            height=620,
        )

        return fig

    except Exception as e:
        st.error(f"Error generating 3D Globe: {e}")
        return None

@st.cache_data(hash_funcs={"xarray.core.dataset.Dataset": id})
def generate_time_series(dataset, variable, lat, lon):
    """
    Generate a line graph showing how a variable changes over time at a given location.
    Automatically normalizes units and labels axes using variable_adapter.
    """
    ts_data = get_location_timeseries(dataset, variable, lat, lon)
    if ts_data is None:
        return None
        
    try:
        var_info = get_variable_info(dataset, variable)
        units = var_info['display_units']
        units_label = f" ({units})" if units else ""
        
        lat_name = 'lat' if 'lat' in ts_data.coords else 'latitude' if 'latitude' in ts_data.coords else None
        lon_name = 'lon' if 'lon' in ts_data.coords else 'longitude' if 'longitude' in ts_data.coords else None
        
        actual_lat = float(ts_data[lat_name].values) if lat_name else lat
        actual_lon = float(ts_data[lon_name].values) if lon_name else lon
        
        df = ts_data.to_dataframe().reset_index()
        
        # Verify time column exists and convert to datetime if needed
        time_col = 'time'
        if time_col not in df.columns:
            st.warning("Time dimension not found for time series.")
            return None
        
        # Apply unit normalization (K→°C, Pa→hPa)
        df[variable] = normalize_values(df[variable].values, var_info)
        
        df[time_col] = pd.to_datetime(df[time_col])
        df = df.set_index(time_col)
        
        # Resample logic based on data duration
        total_days = (df.index.max() - df.index.min()).days
        if total_days > 180:
            resampled_df = df.resample('W').mean().reset_index()
            resample_label = 'Weekly Average'
        elif total_days > 30:
            resampled_df = df.resample('D').mean().reset_index()
            resample_label = 'Daily Average'
        else:
            resampled_df = df.reset_index()
            resample_label = 'Raw Data (No Resampling)'

        # Format time for cleaner hovers
        resampled_df['time_str'] = resampled_df[time_col].dt.strftime('%Y-%m-%d')
            
        fig = go.Figure()
        
        # Smooth line for resampled data
        fig.add_trace(go.Scatter(
            x=resampled_df[time_col], 
            y=resampled_df[variable],
            mode='lines',
            line=dict(color='#38bdf8', width=3, shape='spline', smoothing=0.8),
            name=resample_label,
            hovertemplate=f"Date: %{{text}}<br>Value: %{{y:.3f}}{units_label}<extra></extra>",
            text=resampled_df['time_str']
        ))
        
        title_str = f"Temporal Trend of {variable}{units_label} at Lat {actual_lat:.2f}, Lon {actual_lon:.2f}"
        
        fig.update_layout(
            title=title_str,
            xaxis_title="Time",
            yaxis_title=f"{variable}{units_label}",
            template="plotly_dark",
            hovermode="x unified",
            xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            margin={"r": 0, "t": 60, "l": 0, "b": 0},
            paper_bgcolor='#0e1117',
            plot_bgcolor='#0e1117'
        )
        return fig
    except Exception as e:
        st.error(f"Error generating time series: {e}")
        return None

def generate_climate_animation(dataset, variable):
    """
    Generate an animated heatmap showing climate change over the entire time dimension.
    Uses adaptive color scale and unit normalization via variable_adapter.
    """
    if dataset is None or variable not in dataset:
        st.error(f"Variable '{variable}' not found in the dataset.")
        return None
        
    data = dataset[variable]
    
    if 'time' not in data.dims:
        st.warning(f"Variable '{variable}' does not have a time dimension to animate.")
        return None
        
    try:
        var_info = get_variable_info(dataset, variable)
        units = var_info['display_units']
        units_label = f" ({units})" if units else ""

        # Isolate extra dimensions
        for dim in data.dims:
            if dim not in ['time', 'lat', 'latitude', 'lon', 'longitude']:
                data = data.isel({dim: 0})
                
        # Downsample time if there are too many frames to prevent browser crashes
        time_vals = data.time.values
        time_len = len(time_vals)
        step = max(1, time_len // 50)  # Target ~50 frames max
        
        sampled_times = time_vals[0::step]
        data_sampled = data.sel(time=sampled_times, method='nearest')
        
        lat_col = 'lat' if 'lat' in data_sampled.dims else 'latitude' if 'latitude' in data_sampled.dims else None
        lon_col = 'lon' if 'lon' in data_sampled.dims else 'longitude' if 'longitude' in data_sampled.dims else None
        
        if lat_col and lon_col:
            if data_sampled[lon_col].max() > 180:
                data_sampled.coords[lon_col] = (data_sampled.coords[lon_col] + 180) % 360 - 180
                data_sampled = data_sampled.sortby(lon_col)
            # Downsample to a lightweight grid for fluid animation
            new_lats = np.linspace(float(data_sampled[lat_col].min()), float(data_sampled[lat_col].max()), 35)
            new_lons = np.linspace(float(data_sampled[lon_col].min()), float(data_sampled[lon_col].max()), 70)
            data_sampled = data_sampled.interp({lat_col: new_lats, lon_col: new_lons}, method='linear')
            
        data_sampled = data_sampled.transpose('time', lat_col, lon_col)
            
        # Apply unit normalization (K→°C, Pa→hPa)
        z_values = data_sampled.values
        z_values = normalize_values(z_values, var_info)

        # Apply Gaussian smoothing over the spatial dimensions
        import scipy.ndimage as ndimage
        z_mean = np.nanmean(z_values)
        z_filled = np.nan_to_num(z_values, nan=z_mean)
        
        z_smoothed = ndimage.gaussian_filter(z_filled, sigma=(0, 1.2, 1.2))
        z_smoothed[np.isnan(z_values)] = np.nan
        data_sampled.values = z_smoothed

        # Convert to DataFrame for Plotly express animation
        df = data_sampled.to_dataframe(name='z').reset_index().dropna(subset=['z'])
        
        # Format the time strings for frame names and animation slider
        time_col = 'time'
        if pd.api.types.is_datetime64_any_dtype(df[time_col]):
            df['time_str'] = df[time_col].dt.strftime('%Y-%m-%d')
        else:
            df['time_str'] = df[time_col].astype(str).str.split(' ').str[0]
            
        # Compute global percentile-based range locked across all frames
        color_range, midpoint = compute_color_range(z_smoothed[~np.isnan(z_smoothed)], var_info)
        
        fig = px.scatter_geo(
            df,
            lon=lon_col,
            lat=lat_col,
            color='z',
            animation_frame='time_str',
            projection="natural earth",
            color_continuous_scale=var_info['color_scale'],
            range_color=color_range,
            color_continuous_midpoint=midpoint
        )
        
        fig.update_traces(
            marker=dict(symbol='square', size=7, opacity=0.95),
            hovertemplate=f"Lat: %{{lat:.2f}}<br>Lon: %{{lon:.2f}}<br>Value: %{{marker.color:.2f}}{units_label}<extra></extra>"
        )

        fig.update_layout(
            title=f"Animated Global Distribution: {variable}{units_label}",
            geo=dict(
                showcoastlines=True,
                coastlinecolor='white',
                showcountries=True,
                countrycolor='#484f58',
                bgcolor='#0e1117'
            ),
            uirevision='constant',
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            paper_bgcolor='#0e1117',
            plot_bgcolor='#0e1117'
        )
        return fig
        
    except Exception as e:
        st.error(f"Error generating climate animation: {e}")
        return None

def generate_difference_heatmap(dataset, variable, time1, time2):
    """
    Generate a heatmap showing the difference (time2 - time1) for a climate variable.
    Applies Gaussian smoothing to the anomaly field to remove grid artifacts.
    """
    try:
        df1 = _get_smoothed_spatial_df(dataset, variable, time1)
        df2 = _get_smoothed_spatial_df(dataset, variable, time2)
        
        if df1 is None or df2 is None or df1.empty or df2.empty:
            return None
            
        var_info = get_variable_info(dataset, variable)
        units = var_info['display_units']
        units_label = f" ({units})" if units else ""
            
        # Calculate exactly overlapping difference (since grids are interpolated identically)
        df_diff = df2.copy()
        diff_raw = df2['z'].values - df1['z'].values
        
        # Re-smooth the anomaly field to remove any residual grid artifacts
        # Reshape to 2D grid, smooth, flatten back
        unique_lats = np.sort(df_diff['lat'].unique())
        unique_lons = np.sort(df_diff['lon'].unique())
        
        if len(unique_lats) > 1 and len(unique_lons) > 1:
            import scipy.ndimage as ndimage
            # Build a 2D grid from the flat data for smoothing
            from scipy.interpolate import griddata
            lon_grid, lat_grid = np.meshgrid(unique_lons, unique_lats)
            diff_grid = griddata(
                (df_diff['lon'].values, df_diff['lat'].values),
                diff_raw,
                (lon_grid, lat_grid),
                method='nearest'
            )
            # Apply Gaussian smoothing to the anomaly field
            diff_mean = np.nanmean(diff_grid)
            diff_filled = np.nan_to_num(diff_grid, nan=diff_mean)
            diff_smoothed = ndimage.gaussian_filter(diff_filled, sigma=1.5)
            diff_smoothed[np.isnan(diff_grid)] = np.nan
            
            # Rebuild the flat DataFrame from the smoothed grid
            df_diff = pd.DataFrame({
                'lon': lon_grid.flatten(),
                'lat': lat_grid.flatten(),
                'z': diff_smoothed.flatten()
            }).dropna()
        else:
            df_diff['z'] = diff_raw
        
        # Percentile-based symmetric color range centered at 0
        clean_z = df_diff['z'].dropna().values
        if len(clean_z) > 0:
            vmin = float(np.percentile(clean_z, 2))
            vmax = float(np.percentile(clean_z, 98))
            z_max_abs = max(abs(vmin), abs(vmax))
        else:
            z_max_abs = 1.0
        
        fig = px.scatter_geo(
            df_diff,
            lon='lon',
            lat='lat',
            color='z',
            projection="natural earth",
            color_continuous_scale='RdBu_r',
            color_continuous_midpoint=0,
            range_color=[-z_max_abs if z_max_abs > 0 else -1, z_max_abs if z_max_abs > 0 else 1]
        )
        
        fig.update_traces(
            marker=dict(symbol='square', size=5, opacity=0.95, line=dict(width=0)),
            hovertemplate=f"Lat: %{{lat:.2f}}<br>Lon: %{{lon:.2f}}<br>Change: %{{marker.color:.2f}}{units_label}<extra></extra>"
        )
        
        # Format times for title
        try:
            t1_str = pd.to_datetime(time1).strftime('%Y-%m-%d')
            t2_str = pd.to_datetime(time2).strftime('%Y-%m-%d')
        except:
            t1_str = str(time1)
            t2_str = str(time2)
            
        fig.update_layout(
            title=f"Anomaly: {variable} Change ({t2_str} minus {t1_str})",
            geo=dict(
                showcoastlines=True,
                coastlinecolor='white',
                showcountries=True,
                countrycolor='#484f58',
                bgcolor='#0e1117'
            ),
            uirevision='constant',
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            paper_bgcolor='#0e1117',
            plot_bgcolor='#0e1117'
        )
        return fig
    except Exception as e:
        st.error(f"Error generating difference heatmap: {e}")
        return None

def generate_scattergeo(dataset, variable, time_index=None):
    """
    Generate a global climate visualization using Plotly ScatterGeo.
    """
    df_clean, lat_col, lon_col = _prepare_spatial_data(dataset, variable, time_index)
    
    if df_clean is None:
        return None
        
    try:
        fig = px.scatter_geo(
            df_clean,
            lat=lat_col,
            lon=lon_col,
            color=variable,
            projection="natural earth",
            color_continuous_scale="Bluered",
            hover_data={lat_col: True, lon_col: True, variable: True}
        )
        
        fig.update_layout(
            title=f"Global ScatterGeo: {variable}",
            margin={"r": 0, "t": 40, "l": 0, "b": 0}
        )
        return fig
    except Exception as e:
        st.error(f"Error generating ScatterGeo map: {e}")
        return None
