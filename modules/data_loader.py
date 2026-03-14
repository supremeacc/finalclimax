import xarray as xr
import pandas as pd
import streamlit as st
import numpy as np
@st.cache_data
def load_dataset(file_path):
    """
    Load a NetCDF dataset using xarray.
    Cached to prevent reloading on every Streamlit interaction.
    """
    try:
        # engine='netcdf4' makes sure it can read correctly, chunks help with performance on large files if dask is available
        ds = xr.open_dataset(file_path)
        return ds
    except FileNotFoundError:
        st.error(f"Error: Dataset not found at {file_path}")
        return None
    except Exception as e:
        st.error(f"Error loading dataset: {e}")
        return None

def get_available_variables(dataset):
    """
    Extract a list of distinct data variables from the dataset.
    """
    if dataset is None:
        return []
    
    try:
        # Automatically detect variables from the dataset
        variables = list(dataset.data_vars)
        return variables
    except Exception as e:
        st.error(f"Error extracting variables: {e}")
        return []

def get_time_range(dataset):
    """
    Extract the time range from the dataset.
    """
    if dataset is None:
        return []
        
    try:
        if 'time' in dataset.dims or 'time' in dataset.coords:
            times = dataset['time'].values
            return times
        else:
            return []
    except Exception as e:
        st.error(f"Error extracting time range: {e}")
        return []

@st.cache_data(hash_funcs={"xarray.core.dataset.Dataset": id})
def get_spatial_slice(dataset, variable, time_index=None):
    """
    Extract a 2D spatial slice for a given variable and time index.
    Efficiently slices the xarray dataset before converting to pandas.
    """
    if dataset is None or variable not in dataset:
        return None
        
    data = dataset[variable]
    
    # Handle time slicing
    if time_index is not None and 'time' in data.dims:
        try:
            # 1. Convert any incoming UI selected time formats to Pandas Datetime first to clean them
            try:
                pd_time = pd.to_datetime(time_index)
                time_idx_np = pd_time.to_datetime64()
            except Exception:
                time_idx_np = np.datetime64(time_index) # fallback

            # Add error handling if time value is outside dataset range
            min_time = dataset['time'].min().values
            max_time = dataset['time'].max().values
            
            # Use converted time for bounds check
            if time_idx_np < min_time or time_idx_np > max_time:
                st.error(f"Selected time {time_index} is outside the dataset range ({min_time} to {max_time}).")
                return None
                
            # 2. Use the cleaned pd_time datetime for selecting, not the raw UI input
            data = data.sel(time=pd_time, method='nearest')
        except Exception as e:
            st.error(f"Error selecting time slice: {e}")
            return None
            
    return data

@st.cache_data(hash_funcs={"xarray.core.dataset.Dataset": id})
def get_location_timeseries(dataset, variable, lat, lon):
    """
    Extract a 1D time series for a specific location.
    Uses nearest-neighbor selection for latitude and longitude.
    """
    if dataset is None or variable not in dataset:
        return None
        
    data = dataset[variable]
    
    if 'time' not in data.dims:
        return None
        
    try:
        lat_name = 'lat' if 'lat' in dataset.dims or 'lat' in dataset.coords else 'latitude' if 'latitude' in dataset.dims or 'latitude' in dataset.coords else None
        lon_name = 'lon' if 'lon' in dataset.dims or 'lon' in dataset.coords else 'longitude' if 'longitude' in dataset.dims or 'longitude' in dataset.coords else None
        
        if not lat_name or not lon_name:
            st.error("Could not find latitude/longitude dimension names in the dataset.")
            return None
            
        # Efficiently extract the 1D time series along the selected lat/lon
        ts_data = data.sel({lat_name: lat, lon_name: lon}, method='nearest')
        return ts_data
    except Exception as e:
        st.error(f"Error extracting time series: {e}")
        return None
