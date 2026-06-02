import argparse
import logging
from pathlib import Path

import geopandas as gpd

from cool_routes.utils.paths import (
    REFERENCE_DATA_DIR,
    PROCESSED_DATA_DIR,
)

from cool_routes.utils.log_config import configure_logging


def find_buildings_file(region_slug: str) -> Path:
    """
    Find buildings GeoJSON for a region.
    """

    pattern = f"buildings_height_{region_slug}_*.geojson"

    matches = list(REFERENCE_DATA_DIR.glob(pattern))

    if not matches:
        raise FileNotFoundError(
            f"No buildings file found for region: {region_slug}"
        )

    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple buildings files found: {matches}"
        )

    return matches[0]


def preprocess_buildings(
    gdf: gpd.GeoDataFrame,
    target_crs: int = 32719,
) -> gpd.GeoDataFrame:
    """
    Clean and standardize buildings dataset.
    """

    gdf = gdf.rename(columns={"mean": "height"})

    gdf = gdf.to_crs(target_crs)

    gdf = gdf.dropna(subset=["height"])

    gdf = gdf[gdf.geometry.is_valid]

    return gdf


def main(region_slug: str):

    configure_logging("INFO")
    logger = logging.getLogger(__name__)

    logger.info(f"Processing buildings for region: {region_slug}")

    input_path = find_buildings_file(region_slug)

    logger.info(f"Loading: {input_path.name}")

    gdf = gpd.read_file(input_path)

    logger.info("Preprocessing buildings")

    gdf = preprocess_buildings(gdf)

    output_dir = PROCESSED_DATA_DIR / "buildings"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"buildings_{region_slug}.parquet"

    logger.info(f"Saving: {output_path.name}")

    gdf.to_parquet(output_path)

    logger.info("Buildings preprocessing completed")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--region",
        required=True,
        type=str,
        help="Region slug",
    )

    args = parser.parse_args()

    main(args.region)