import argparse
import logging

from cool_routes.network.graph import (
    download_walk_network,
    preprocess_edges,
)

from cool_routes.utils.load_yaml import load_yaml
from cool_routes.utils.log_config import configure_logging
from cool_routes.utils.paths import (
    CONFIG_DIR,
    PROCESSED_DATA_DIR,
)


# =================================================
# Config
# =================================================

REGIONS_DIR = CONFIG_DIR / "regions"


# =================================================
# Main
# =================================================

def main(region_slug: str):

    # ---- Logging

    configure_logging("INFO")
    logger = logging.getLogger(__name__)

    logger.info("Building pedestrian network")

    # ---- Load region config

    region_cfg = load_yaml(
        REGIONS_DIR / f"{region_slug}.yaml"
    )

    place_name = region_cfg["region"]["place_name"]

    logger.info(f"Downloading graph: {place_name}")

    # ---- Download graph

    nodes, edges = download_walk_network(
        place_name
    )

    logger.info(
        f"Downloaded {len(edges)} edges"
    )

    # ---- Preprocess

    edges = preprocess_edges(edges)

    # ---- Output

    output_dir = (
        PROCESSED_DATA_DIR
        / "network"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / f"walk_edges_{region_slug}.parquet"
    )

    logger.info(f"Saving graph: {output_path}")

    edges.to_parquet(output_path)

    logger.info("Network build completed")


# =================================================
# CLI
# =================================================

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