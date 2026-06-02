"""
Utilities for pedestrian network download and preprocessing.
"""

import geopandas as gpd
import osmnx as ox


# =================================================
# Download graph
# =================================================

def download_walk_network(
    place_name: str,
):
    """
    Download pedestrian network from OpenStreetMap.

    Parameters
    ----------
    place_name : str
        Place name compatible with OSMnx.

    Returns
    -------
    tuple
        nodes, edges GeoDataFrames.
    """

    graph = ox.graph_from_place(
        place_name,
        network_type="walk",
    )

    nodes, edges = ox.graph_to_gdfs(graph)

    return nodes, edges


# =================================================
# Helpers
# =================================================

def normalize_osm_value(value):
    """
    Normalize OSM values for parquet compatibility.
    """

    if isinstance(value, list):
        return " / ".join(map(str, value))

    if isinstance(value, tuple):
        return " / ".join(map(str, value))

    if isinstance(value, dict):
        return str(value)

    return value


def clean_object_columns(
    gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:

    gdf = gdf.copy()

    object_cols = gdf.select_dtypes(
        include=["object"]
    ).columns

    for col in object_cols:

        gdf[col] = gdf[col].apply(
            normalize_osm_value
        )

        gdf[col] = gdf[col].astype(
            "string"
        )

    return gdf


def drop_fully_empty_columns(
    gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Drop columns containing only null values.
    """

    return gdf.dropna(
        axis=1,
        how="all",
    )


# =================================================
# Preprocess edges
# =================================================

def preprocess_edges(
    edges_gdf: gpd.GeoDataFrame,
    *,
    epsg: int = 32719,
) -> gpd.GeoDataFrame:
    """
    Preprocess pedestrian network edges.

    Steps
    -----
    1. Reset graph topology index.
    2. Reproject to projected CRS.
    3. Create unique edge_id.
    4. Compute edge length.
    5. Normalize object columns.
    6. Remove fully empty columns.

    Parameters
    ----------
    edges_gdf : GeoDataFrame
        Raw OSMnx edges.

    epsg : int
        Projected CRS.

    Returns
    -------
    GeoDataFrame
        Cleaned edge GeoDataFrame.
    """

    edges = edges_gdf.copy()

    # -------------------------------------------------
    # Preserve graph topology
    # -------------------------------------------------

    edges = edges.reset_index()

    # -------------------------------------------------
    # Reproject to metric CRS
    # -------------------------------------------------

    edges = edges.to_crs(epsg=epsg)

    # -------------------------------------------------
    # Unique edge id
    # -------------------------------------------------

    edges["edge_id"] = range(len(edges))

    # -------------------------------------------------
    # Edge length
    # -------------------------------------------------

    edges["edge_length"] = edges.geometry.length

    # -------------------------------------------------
    # Normalize problematic object columns
    # -------------------------------------------------

    edges = clean_object_columns(edges)

    # -------------------------------------------------
    # Remove empty columns
    # -------------------------------------------------

    edges = drop_fully_empty_columns(edges)

    return edges


# =================================================
# Restore graph
# =================================================

def restore_graph(
    nodes_gdf: gpd.GeoDataFrame,
    edges_gdf: gpd.GeoDataFrame,
):
    """
    Restore NetworkX graph from processed edges.

    Parameters
    ----------
    nodes_gdf : GeoDataFrame
        Nodes GeoDataFrame.

    edges_gdf : GeoDataFrame
        Processed/enriched edges GeoDataFrame.

    Returns
    -------
    networkx.MultiDiGraph
        Restored routing graph.
    """

    required_cols = ["u", "v", "key"]

    missing = [
        col for col in required_cols
        if col not in edges_gdf.columns
    ]

    if missing:
        raise ValueError(
            f"Missing topology columns: {missing}"
        )

    edges = edges_gdf.set_index(
        ["u", "v", "key"]
    )

    graph = ox.graph_from_gdfs(
        nodes_gdf,
        edges,
    )

    return graph