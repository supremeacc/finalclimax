"""
Helper functions for ClimaScope.
Contains utility functions for data manipulation, unit conversions, and calculations.
"""

def celsius_to_fahrenheit(celsius):
    """
    Convert temperature from Celsius to Fahrenheit.
    """
    return (celsius * 9/5) + 32

def ms_to_kmh(ms):
    """
    Convert wind speed from meters per second to kilometers per hour.
    """
    return ms * 3.6

def calculate_anomaly(dataset, variable, baseline_years):
    """
    Calculate the climate anomaly relative to a baseline period.
    This is a stub function for future bonus feature implementation.
    
    Args:
        dataset (xarray.Dataset): The climate dataset.
        variable (str): the variable name.
        baseline_years (tuple): A tuple of (start_year, end_year).
    Returns:
        xarray.DataArray: Anomaly data
    """
    # Requires grouping by 'time.month' and subtracting the mean climatology
    pass
