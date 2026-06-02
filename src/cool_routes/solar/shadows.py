"""
Lógica de cálculo posición del sol,
proyección de sombra y % de sombra en tramo de calle
"""

from datetime import datetime
from typing import Tuple

import geopandas as gpd
import numpy as np

from pysolar.solar import get_altitude, get_azimuth
from shapely.affinity import translate


# =================================================
# Solar position
# =================================================

def get_solar_position(
    lat: float,
    lon: float,
    dt: datetime,
) -> Tuple[float, float]:
    """
    Compute solar altitude and azimuth.

    Parameters
    ----------
    lat : float
        Latitude.

    lon : float
        Longitude.

    dt : datetime
        Timezone-aware datetime.

    Returns
    -------
    tuple[float, float]
        Solar altitude and azimuth in degrees.
    """

    altitude = get_altitude(lat, lon, dt)
    azimuth = get_azimuth(lat, lon, dt)

    return altitude, azimuth


# =================================================
# Shadow length
# =================================================

def compute_shadow_length(
    buildings_gdf: gpd.GeoDataFrame,
    *,
    height_col: str = "height",
    solar_altitude: float,
) -> gpd.GeoDataFrame:
    """
    Compute shadow length for buildings.

    Parameters
    ----------
    buildings_gdf : GeoDataFrame
        Buildings GeoDataFrame.

    height_col : str
        Building height column.

    solar_altitude : float
        Solar altitude angle in degrees.

    Returns
    -------
    GeoDataFrame
        Buildings with shadow length column.
    """

    gdf = buildings_gdf.copy()

    altitude_rad = np.radians(solar_altitude)

    # Sun below horizon
    if solar_altitude <= 0:
        gdf["shadow_length"] = 0.0
        return gdf

    gdf["shadow_length"] = (
        gdf[height_col] / np.tan(altitude_rad)
    )

    return gdf


# =================================================
# Shadow projection
# =================================================

def project_building_shadows(
    buildings_gdf: gpd.GeoDataFrame,
    *,
    solar_azimuth: float,
    shadow_col: str = "shadow_length",
) -> gpd.GeoDataFrame:
    """
    Project building shadows using solar azimuth.

    Parameters
    ----------
    buildings_gdf : GeoDataFrame
        Buildings GeoDataFrame with shadow lengths.

    solar_azimuth : float
        Solar azimuth angle in degrees.

    shadow_col : str
        Column containing shadow length.

    Returns
    -------
    GeoDataFrame
        GeoDataFrame with projected shadow geometry.
    """

    gdf = buildings_gdf.copy()

    azimuth_rad = np.radians(solar_azimuth)

    dx = np.sin(azimuth_rad)
    dy = np.cos(azimuth_rad)

    def _project(row):

        distance = row[shadow_col]

        return translate(
            row.geometry,
            xoff=dx * distance,
            yoff=dy * distance,
        )

    # Preserve original building geometry
    gdf["building_geometry"] = gdf.geometry

    # Create projected shadow geometry
    gdf["shadow_geometry"] = gdf.apply(
        _project,
        axis=1,
    )

    # Set shadow geometry as active geometry
    shadows_gdf = gdf.set_geometry(
        "shadow_geometry"
    )

    if buildings_gdf.crs is None:
        raise ValueError(
            "Buildings GeoDataFrame must have a CRS"
        )

    if not buildings_gdf.crs.is_projected:
        raise ValueError(
            "Buildings GeoDataFrame must use projected CRS"
        )
    
    return shadows_gdf


# =================================================
# Full pipeline
# =================================================

def generate_shadows(
    buildings_gdf: gpd.GeoDataFrame,
    *,
    lat: float,
    lon: float,
    dt: datetime,
    height_col: str = "height",
) -> gpd.GeoDataFrame:
    """
    Generate projected building shadows.

    Parameters
    ----------
    buildings_gdf : GeoDataFrame
        Buildings GeoDataFrame.

    lat : float
        Latitude.

    lon : float
        Longitude.

    dt : datetime
        Timezone-aware datetime.

    height_col : str
        Building height column.

    Returns
    -------
    GeoDataFrame
        Buildings enriched with:
        - building geometry
        - shadow geometry
        - shadow length
        - solar metadata
    """

    solar_altitude, solar_azimuth = get_solar_position(
        lat,
        lon,
        dt,
    )

    buildings = compute_shadow_length(
        buildings_gdf,
        height_col=height_col,
        solar_altitude=solar_altitude,
    )

    shadows = project_building_shadows(
        buildings,
        solar_azimuth=solar_azimuth,
    )

    # Add solar metadata
    shadows["solar_altitude"] = solar_altitude
    shadows["solar_azimuth"] = solar_azimuth
    shadows["shadow_datetime"] = dt

    return shadows