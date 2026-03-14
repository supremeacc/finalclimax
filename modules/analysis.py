import numpy as np
import pandas as pd
import streamlit as st


@st.cache_data(hash_funcs={"xarray.core.dataset.Dataset": id})
def compute_climate_insights(dataset, variable):
    """
    Compute summary statistics for a climate variable across the entire dataset.
    
    Returns a dictionary with:
      - global_avg: The global average value across all space and time.
      - max_value: The maximum value.
      - max_location: (lat, lon, time) of the maximum value.
      - min_value: The minimum value.
      - min_location: (lat, lon, time) of the minimum value.
      - largest_change: The largest absolute change between consecutive time steps.
      - largest_change_times: (time_from, time_to) of the largest change.
    """
    if dataset is None or variable not in dataset:
        return None
        
    data = dataset[variable]
    
    lat_name = 'lat' if 'lat' in dataset.coords else 'latitude' if 'latitude' in dataset.coords else None
    lon_name = 'lon' if 'lon' in dataset.coords else 'longitude' if 'longitude' in dataset.coords else None
    
    if not lat_name or not lon_name:
        return None
        
    try:
        insights = {}
        
        # 1. Global average value
        insights['global_avg'] = float(data.mean().values)
        
        # 2. Maximum value and location
        max_idx = data.argmax(dim=...)
        insights['max_value'] = float(data.max().values)
        max_lat = float(dataset[lat_name].values[max_idx[lat_name].values])
        max_lon = float(dataset[lon_name].values[max_idx[lon_name].values])
        if 'time' in max_idx:
            try:
                max_time = pd.to_datetime(dataset['time'].values[max_idx['time'].values]).strftime('%Y-%m-%d')
            except:
                max_time = str(dataset['time'].values[max_idx['time'].values])
            insights['max_location'] = f"{max_lat:.2f}°, {max_lon:.2f}° on {max_time}"
        else:
            insights['max_location'] = f"{max_lat:.2f}°, {max_lon:.2f}°"
        
        # 3. Minimum value and location
        min_idx = data.argmin(dim=...)
        insights['min_value'] = float(data.min().values)
        min_lat = float(dataset[lat_name].values[min_idx[lat_name].values])
        min_lon = float(dataset[lon_name].values[min_idx[lon_name].values])
        if 'time' in min_idx:
            try:
                min_time = pd.to_datetime(dataset['time'].values[min_idx['time'].values]).strftime('%Y-%m-%d')
            except:
                min_time = str(dataset['time'].values[min_idx['time'].values])
            insights['min_location'] = f"{min_lat:.2f}°, {min_lon:.2f}° on {min_time}"
        else:
            insights['min_location'] = f"{min_lat:.2f}°, {min_lon:.2f}°"
        
        # 4. Largest change between consecutive time steps
        if 'time' in data.dims and len(data.time) > 1:
            # Compute the mean across space for each time step, then diff
            spatial_mean = data.mean(dim=[lat_name, lon_name])
            diffs = spatial_mean.diff(dim='time')
            abs_diffs = np.abs(diffs)
            
            max_change_idx = int(abs_diffs.argmax(dim='time').values)
            max_change_time = diffs.time.values[max_change_idx]
            insights['largest_change'] = float(diffs.sel(time=max_change_time, method='nearest').values)
            
            try:
                t_from = pd.to_datetime(data.time.values[max_change_idx]).strftime('%Y-%m-%d')
                t_to = pd.to_datetime(data.time.values[max_change_idx + 1]).strftime('%Y-%m-%d')
            except:
                t_from = str(data.time.values[max_change_idx])
                t_to = str(data.time.values[max_change_idx + 1])
                
            insights['largest_change_times'] = f"{t_from} → {t_to}"
        else:
            insights['largest_change'] = None
            insights['largest_change_times'] = None
        
        return insights
        
    except Exception as e:
        st.error(f"Error computing climate insights: {e}")
        return None
