"""
Variable adapter module for automatic dataset adaptation.

Detects variable types and units from NetCDF metadata, applies normalization
(K→°C, Pa→hPa), selects appropriate color scales, and computes percentile-based
color ranges so the dashboard adapts to any climate dataset automatically.
"""

import numpy as np
import streamlit as st


# ── Variable type classification ──────────────────────────────────────────────

_TEMPERATURE_NAMES = {'air', 'tmp', 'temp', 'temperature', 'tas', 'tas2m', 't2m', 'sst', 'skt'}
_WIND_NAMES = {'uwnd', 'vwnd', 'u', 'v', 'u10', 'v10', 'uwind', 'vwind', 'wspd'}
_PRECIP_NAMES = {'precip', 'precipitation', 'pr', 'prate', 'rain', 'rainfall', 'tp', 'prcp'}
_PRESSURE_NAMES = {'pres', 'pressure', 'slp', 'mslp', 'msl', 'prmsl', 'sp', 'ps'}


def _classify_variable(variable_name, units):
    """Classify a variable into a category based on its name and units."""
    name_lower = variable_name.lower()

    # Check by units first (most reliable)
    if units:
        units_lower = units.lower().strip()
        if units_lower in ('k', 'kelvin', 'degc', 'deg_c', 'celsius', '°c', 'degrees_celsius', 'degrees_c'):
            return 'temperature'
        if units_lower in ('pa', 'hpa', 'mb', 'mbar', 'pascal', 'hectopascal'):
            return 'pressure'
        if units_lower in ('m/s', 'm s-1', 'm s**-1', 'knots', 'kt'):
            return 'wind'
        if units_lower in ('mm', 'mm/day', 'mm/hr', 'kg m-2 s-1', 'kg/m2/s', 'mm/h', 'mm day-1'):
            return 'precipitation'

    # Fallback: check by variable name
    if name_lower in _TEMPERATURE_NAMES or any(t in name_lower for t in ('temp', 'sst')):
        return 'temperature'
    if name_lower in _WIND_NAMES or any(w in name_lower for w in ('wnd', 'wind')):
        return 'wind'
    if name_lower in _PRECIP_NAMES or any(p in name_lower for p in ('precip', 'rain')):
        return 'precipitation'
    if name_lower in _PRESSURE_NAMES or any(p in name_lower for p in ('pres', 'slp')):
        return 'pressure'

    return 'generic'


# ── Public API ────────────────────────────────────────────────────────────────

@st.cache_data(hash_funcs={"xarray.core.dataset.Dataset": id})
def get_variable_info(dataset, variable):
    """
    Inspect a dataset variable and return adaptation metadata.

    Returns a dict with:
        - category: str  ('temperature', 'wind', 'precipitation', 'pressure', 'generic')
        - raw_units: str | None  (original units from attrs)
        - display_units: str     (units after normalization)
        - color_scale: str       (Plotly color scale name)
        - center_zero: bool      (whether the color scale should be centered at 0)
        - needs_kelvin_offset: bool
        - needs_pa_to_hpa: bool
    """
    if dataset is None or variable not in dataset:
        return _default_info()

    da = dataset[variable]
    raw_units = da.attrs.get('units', da.attrs.get('unit', None))
    category = _classify_variable(variable, raw_units)

    info = {
        'category': category,
        'raw_units': raw_units,
        'display_units': raw_units or '',
        'color_scale': 'RdBu_r',
        'center_zero': True,
        'needs_kelvin_offset': False,
        'needs_pa_to_hpa': False,
    }

    # ── Temperature ────────────────────────────────────────────
    if category == 'temperature':
        info['color_scale'] = 'Turbo'
        info['center_zero'] = False
        if raw_units and raw_units.lower().strip() in ('k', 'kelvin'):
            info['needs_kelvin_offset'] = True
            info['display_units'] = '°C'
        elif raw_units:
            info['display_units'] = raw_units
        else:
            info['display_units'] = '°C'

    # ── Pressure ───────────────────────────────────────────────
    elif category == 'pressure':
        info['color_scale'] = 'Viridis'
        info['center_zero'] = False
        if raw_units and raw_units.lower().strip() in ('pa', 'pascal'):
            info['needs_pa_to_hpa'] = True
            info['display_units'] = 'hPa'
        elif raw_units:
            info['display_units'] = raw_units
        else:
            info['display_units'] = 'hPa'

    # ── Wind ───────────────────────────────────────────────────
    elif category == 'wind':
        info['color_scale'] = 'Plasma'
        info['center_zero'] = True
        info['display_units'] = raw_units or 'm/s'

    # ── Precipitation ──────────────────────────────────────────
    elif category == 'precipitation':
        info['color_scale'] = 'Cividis'
        info['center_zero'] = False
        info['display_units'] = raw_units or 'mm'

    # ── Generic / unknown ──────────────────────────────────────
    else:
        info['color_scale'] = 'Turbo'
        info['center_zero'] = False
        info['display_units'] = raw_units or ''

    return info


def normalize_values(values, var_info):
    """
    Apply unit conversions in-place on a numpy array or pandas Series.
    Returns the (possibly modified) values.
    """
    if var_info.get('needs_kelvin_offset'):
        values = values - 273.15
    if var_info.get('needs_pa_to_hpa'):
        values = values / 100.0
    return values


def compute_color_range(values, var_info):
    """
    Compute percentile-based (vmin, vmax) and optional midpoint for the color scale.
    Uses 2nd and 98th percentiles to prevent extreme outliers from washing out the map.

    Returns (range_color, midpoint) where range_color is [vmin, vmax].
    """
    clean = values[~np.isnan(values)] if hasattr(values, '__len__') else values
    if len(clean) == 0:
        return [-1, 1], 0

    vmin = float(np.percentile(clean, 2))
    vmax = float(np.percentile(clean, 98))

    # Prevent degenerate range
    if vmin == vmax:
        vmin -= 1
        vmax += 1

    if var_info.get('center_zero'):
        abs_max = max(abs(vmin), abs(vmax))
        return [-abs_max, abs_max], 0
    else:
        return [vmin, vmax], None


def _default_info():
    return {
        'category': 'generic',
        'raw_units': None,
        'display_units': '',
        'color_scale': 'RdBu_r',
        'center_zero': True,
        'needs_kelvin_offset': False,
        'needs_pa_to_hpa': False,
    }
