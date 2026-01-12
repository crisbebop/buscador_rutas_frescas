from typing import Optional, List, Dict

import ee
import geopandas as gpd
import osmnx as ox

from shapely.geometry import Polygon, shape, mapping


# =================================================
# Initialization
# =================================================

def init_gee(project_id: str) -> None:
    """
    Initialize Google Earth Engine.
    """
    try:
        ee.Initialize(project=project_id)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=project_id)


# =================================================
# Region of Interest (ROI)
# =================================================

def roi_from_place(place_name: str) -> ee.Geometry:
    """
    Obtain ROI from OSM using a place name.
    """
    place_gdf = ox.geocode_to_gdf(place_name)
    polygon = place_gdf.geometry.iloc[0]
    return ee.Geometry.Polygon(list(polygon.exterior.coords))


def roi_from_polygon(coords: List[List[float]]) -> ee.Geometry:
    """
    Obtain ROI from a fallback polygon (lon, lat).
    """
    return ee.Geometry.Polygon(coords)


def get_roi(
    place_name: str,
    fallback_coords: List[List[float]],
) -> ee.Geometry:
    """
    Obtain ROI from place name, fallback to polygon if OSM fails.
    """
    try:
        return roi_from_place(place_name)
    except Exception:
        return roi_from_polygon(fallback_coords)


# =================================================
# Building height dataset (GEE)
# =================================================

def load_temporal_building_height(
    dataset_id: str,
    year: int,
    roi: ee.Geometry,
    height_band: str,
    presence_band: str,
    confidence_threshold: float,
) -> ee.Image:
    """
    Load and mask temporal building height dataset from GEE.
    """
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    collection = (
        ee.ImageCollection(dataset_id)
        .filterDate(start_date, end_date)
        .filterBounds(roi)
    )

    if collection.size().getInfo() == 0:
        raise ValueError("No images found for given year and ROI")

    mosaic = collection.mosaic().clip(roi)

    bands = mosaic.bandNames().getInfo()
    if height_band not in bands or presence_band not in bands:
        raise ValueError("Expected bands not found in dataset")

    height_img = mosaic.select(height_band)
    presence_img = mosaic.select(presence_band)

    mask = presence_img.gt(confidence_threshold)
    return height_img.updateMask(mask)


# =================================================
# OSM building footprints
# =================================================

def get_osm_building_footprints(
    place_name: str,
    tags: Optional[Dict] = None,
) -> gpd.GeoDataFrame:
    """
    Download building footprints from OSM using place name.
    """
    if tags is None:
        tags = {"building": True}

    gdf = ox.features_from_place(place_name, tags=tags)

    gdf = gdf[
        gdf.geometry.apply(
            lambda geom: isinstance(geom, Polygon)
            and geom.is_valid
            and not geom.is_empty
        )
    ]

    if gdf.empty:
        raise ValueError("No building footprints found in OSM")

    return gdf


def gdf_to_ee_feature_collection(
    gdf: gpd.GeoDataFrame,
    id_column: Optional[str] = None,
) -> ee.FeatureCollection:
    """
    Convert GeoDataFrame to Earth Engine FeatureCollection.
    """
    if gdf.empty:
        raise ValueError("GeoDataFrame is empty")

    features = []

    for idx, row in gdf.iterrows():
        ee_geom = ee.Geometry(mapping(row.geometry))

        if id_column and id_column in row:
            props = {"id": str(row[id_column])}
        else:
            props = {"id": str(idx)}

        features.append(ee.Feature(ee_geom, props))

    return ee.FeatureCollection(features)


# =================================================
# Zonal statistics
# =================================================

def extract_mean_height_per_building(
    buildings_fc: ee.FeatureCollection,
    height_image: ee.Image,
    scale: int,
    crs: str = "EPSG:4326",
    tile_scale: int = 4,
) -> ee.FeatureCollection:
    """
    Compute mean building height per footprint.
    """
    return height_image.reduceRegions(
        collection=buildings_fc,
        reducer=ee.Reducer.mean(),
        scale=scale,
        crs=crs,
        tileScale=tile_scale,
    )


# =================================================
# Conversion utilities
# =================================================

def ee_feature_collection_to_gdf(
    fc: ee.FeatureCollection,
) -> gpd.GeoDataFrame:
    """
    Convert Earth Engine FeatureCollection to GeoDataFrame.
    """
    features = fc.getInfo()["features"]

    geometries = []
    properties = []

    for f in features:
        if f["properties"].get("mean") is not None:
            geometries.append(shape(f["geometry"]))
            properties.append(f["properties"])

    if not geometries:
        raise ValueError("No valid features with height values found")

    gdf = gpd.GeoDataFrame(properties, geometry=geometries, crs="EPSG:4326")
    gdf = gdf.rename(columns={"mean": "height_m"})

    return gdf


# =================================================
# Export helpers
# =================================================

def export_feature_collection_to_drive(
    fc: ee.FeatureCollection,
    *,
    description: str,
    filename_prefix: str,
    file_format: str = "GeoJSON",
    folder: str | None = None,
) -> ee.batch.Task:
    """
    Export FeatureCollection to Google Drive.

    Returns
    -------
    ee.batch.Task
        Started export task.
    """
    kwargs = dict(
        collection=fc,
        description=description,
        fileNamePrefix=filename_prefix,
        fileFormat=file_format,
    )

    if folder:
        kwargs["folder"] = folder

    task = ee.batch.Export.table.toDrive(**kwargs)
    task.start()
    return task

def export_image_to_drive(
    image: ee.Image,
    *,
    description: str,
    filename_prefix: str,
    region: ee.Geometry,
    scale: int,
    crs: str,
    folder: str | None = None,
) -> ee.batch.Task:
    """Export raster image (e.g. NDVI) to Google Drive."""
    kwargs = dict(
        image=image,
        description=description,
        fileNamePrefix=filename_prefix,
        region=region,
        scale=scale,
        crs=crs,
        maxPixels=1e13,
    )

    if folder:
        kwargs["folder"] = folder

    task = ee.batch.Export.image.toDrive(**kwargs)
    task.start()
    return task

# -------------------------------------------------
# NDVI (Sentinel-2)
# -------------------------------------------------

def _mask_s2_clouds(image: ee.Image) -> ee.Image:
    """Apply cloud mask using S2 QA60 band."""
    qa = image.select("QA60")
    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit).eq(0).And(
        qa.bitwiseAnd(cirrus_bit).eq(0)
    )
    return image.updateMask(mask).divide(10000)


def load_ndvi(
    start_date: str,
    end_date: str,
    roi: ee.Geometry,
    cloud_percentage: int,
    s2_colection: str,

) -> ee.Image:
    """
    Load NDVI from Sentinel-2 Surface Reflectance.
    """
    collection = (
        ee.ImageCollection(s2_colection)
        .filterDate(start_date, end_date)
        .filterBounds(roi)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_percentage))
        .map(_mask_s2_clouds)
    )

    if collection.size().getInfo() == 0:
        raise ValueError("No Sentinel-2 images found for NDVI")

    ndvi = collection.map(
        lambda img: img.normalizedDifference(["B8", "B4"]).rename("NDVI")
    )

    return ndvi.mean().clip(roi)


# -------------------------------------------------
# Landsat 8 -LST
# -------------------------------------------------

# Landsat 8 – LST constants

LANDSAT_8_LST_COLLECTION = "LANDSAT/LC08/C02/T1_L2"
LANDSAT_8_LST_BAND = "ST_B10"
LANDSAT_8_QA_BAND = "QA_PIXEL" # Landsat usa QA_PIXEL para máscaras de nubes

LANDSAT_8_CLOUD_SHADOW_BIT = 3
LANDSAT_8_CLOUD_BIT = 5
LANDSAT_8_CIRRUS_BIT = 7

LANDSAT_8_LST_SCALE = 0.00341802
LANDSAT_8_LST_OFFSET = 149.0
KELVIN_TO_CELSIUS = 273.15

def load_landsat8_lst_collection(
    *,
    start_date: str,
    end_date: str,
    roi: ee.Geometry,
) -> ee.ImageCollection:
    """
    Load Landsat 8 Collection 2 Tier 1 LST image collection.
    """
    return (
        ee.ImageCollection(LANDSAT_8_LST_COLLECTION)
        .filterDate(start_date, end_date)
        .filterBounds(roi)
    )

def scale_to_celsius(image):
    lst_celsius = (image.select(LANDSAT_8_LST_BAND)
                   .multiply(LANDSAT_8_LST_SCALE)
                   .add(LANDSAT_8_LST_OFFSET)
                   .subtract(KELVIN_TO_CELSIUS)
                   .rename("LST"))
    return image.addBands(lst_celsius)

def apply_landsat8_cloud_mask(image):
    """Aplica la máscara de nubes usando los bits de QA_PIXEL."""
    qa = image.select(LANDSAT_8_QA_BAND)
    
    # Bits: 3=Sombra de nube, 5=Nube, 7=Cirrus
    cloud_shadow = 1 << 3
    clouds = 1 << 5
    cirrus = 1 << 7

    mask = (qa.bitwiseAnd(cloud_shadow).eq(0)
            .And(qa.bitwiseAnd(clouds).eq(0))
            .And(qa.bitwiseAnd(cirrus).eq(0)))
    
    return image.updateMask(mask)

def validate_image_collection(
    collection: ee.ImageCollection,
    *,
    context: str = "",
) -> None:
    """
    Raise error if ImageCollection is empty.
    """
    size = collection.size().getInfo()

    if size == 0:
        raise ValueError(
            f"No images found in ImageCollection. {context}")
    else:
        print(f"Validated Collection: {size} images founded.")


def build_lst_composite(
    *,
    collection: ee.ImageCollection,
    roi: ee.Geometry,
    reducer: str = "median",
) -> ee.Image:
    """
    Build LST composite image from a processed collection.
    """
    if reducer == "median":
        image = collection.select("LST").median()
    elif reducer == "mean":
        image = collection.select("LST").mean()
    else:
        raise ValueError(f"Unsupported reducer: {reducer}")

    return image.clip(roi)
