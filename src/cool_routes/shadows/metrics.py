import geopandas as gpd
from geopandas import overlay


def compute_shadow_metrics(
    edges_gdf: gpd.GeoDataFrame,
    shadows_gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Compute shadow length and shadow percentage
    for each street segment.
    """

    edges = edges_gdf.copy()

    # -----------------------------------------
    # Intersections
    # -----------------------------------------
    if edges.crs != shadows_gdf.crs:
        raise ValueError(
        "Edges and shadows must have the same CRS."
        )


    edges_intersect = overlay(
        edges,
        shadows_gdf,
        how="intersection",
    )

    # -----------------------------------------
    # Shadow length per intersection
    # -----------------------------------------

    edges_intersect["shadow_length"] = (
        edges_intersect.geometry.length
    )

    # -----------------------------------------
    # Aggregate by edge
    # -----------------------------------------

    shadows_by_edge = (
        edges_intersect
        .groupby("edge_id")["shadow_length"]
        .sum()
        .reset_index()
    )

    # -----------------------------------------
    # Merge to original edges
    # -----------------------------------------

    edges = edges.merge(
        shadows_by_edge,
        on="edge_id",
        how="left",
    )

    # -----------------------------------------
    # Fill non-shadowed edges
    # -----------------------------------------

    edges["shadow_length"] = (
        edges["shadow_length"]
        .fillna(0)
    )

    # -----------------------------------------
    # Shadow percentage
    # -----------------------------------------

    edges["pct_shadow"] = (
        edges["shadow_length"]
        / edges["edge_length"]
    ).clip(0, 1)

    return edges