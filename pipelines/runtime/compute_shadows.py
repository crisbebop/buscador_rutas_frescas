import argparse
import logging
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pytz

from cool_routes.solar.shadows import generate_shadows
from cool_routes.utils.load_yaml import load_yaml
from cool_routes.utils.log_config import configure_logging
from cool_routes.utils.paths import (
    CONFIG_DIR,
    PROCESSED_DATA_DIR,
)


# =================================================
# Paths
# =================================================

RUNTIME_CONFIG_DIR = CONFIG_DIR / "runtime"


# =================================================
# Main
# =================================================

def main(region_slug: str):

    # ---- Logging

    configure_logging("INFO")
    logger = logging.getLogger(__name__)

    logger.info("Starting shadow computation")

    # ---- Load config

    config = load_yaml(
        RUNTIME_CONFIG_DIR / "shadow_runtime.yaml"
    )

    # ---- Load buildings

    buildings_path = (
        PROCESSED_DATA_DIR
        / "buildings"
        / f"buildings_{region_slug}.parquet"
    )

    logger.info(f"Loading buildings: {buildings_path}")

    buildings_gdf = gpd.read_parquet(buildings_path)

    # ---- Datetime

    timezone = pytz.timezone(
        config["datetime"]["timezone"]
    )

    dt = timezone.localize(
        datetime(
            config["datetime"]["year"],
            config["datetime"]["month"],
            config["datetime"]["day"],
            config["datetime"]["hour"],
            config["datetime"]["minute"],
        )
    )

    logger.info(f"Using datetime: {dt}")

    # ---- Solar location

    lat = config["location"]["latitude"]
    lon = config["location"]["longitude"]

    # ---- Generate shadows

    logger.info("Generating shadows")

    shadows_gdf = generate_shadows(
        buildings_gdf,
        lat=lat,
        lon=lon,
        dt=dt,
        height_col=config["buildings"]["height_column"],
    )

    # ---- Output

    output_dir = (
        PROCESSED_DATA_DIR
        / "shadows"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = dt.strftime("%Y%m%d_%H%M")

    output_path = (
        output_dir
        / f"shadows_{region_slug}_{timestamp}.parquet"
    )

    logger.info(f"Saving shadows: {output_path}")

    shadows_gdf.to_parquet(output_path)

    logger.info("Shadow computation completed")


# =================================================
# CLI
# =================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--region",
        required=True,
        help="Region slug",
    )

    args = parser.parse_args()

    main(args.region)