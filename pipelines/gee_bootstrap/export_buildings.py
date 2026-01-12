"""
Pipeline: Export building heights from Google Earth Engine.

Responsibility:
- Orchestrate the extraction of building heights
- Export results to Google Drive

Domain logic lives in: cool_routes.ingest.gee
"""

from pathlib import Path
import logging
import yaml
from cool_routes.utils.load_yaml import load_yaml
from cool_routes.utils.log_config import configure_logging

from cool_routes.ingest.gee import (
    init_gee,
    get_roi,
    load_temporal_building_height,
    get_osm_building_footprints,
    gdf_to_ee_feature_collection,
    extract_mean_height_per_building,
    export_feature_collection_to_drive,
)

# =================================================
# Configuration
# =================================================

BASE_DIR = Path(__file__).resolve().parents[2]

CONFIG_DIR = BASE_DIR / "config" / "gee"
REGIONS_DIR = BASE_DIR / "config" / "regions"


def main(region_slug: str):
    # ---- Logging
    configure_logging("INFO")
    logger = logging.getLogger(__name__)

    # ---- Load configs
    # Levanta error si no encuentra region_slug
    region_path = REGIONS_DIR / f"{region_slug}.yaml"
    if not region_path.exists():
        raise ValueError(
            f"Region '{region_slug}' not found. "
            f"Expected file: {region_path.name}"
        )

    region_cfg = load_yaml(region_path)
    export_cfg = load_yaml(CONFIG_DIR / "export_buildings.yaml")
    #globals_cfg = load_yaml(BASE_DIR / "config/globals.yaml")

    # ---- Initialize GEE
    logger.info("Initializing Google Earth Engine")
    init_gee(project_id=export_cfg["gee"]["project_id"])

    # ---- ROI
    logger.info("Resolving region of interest (ROI)")
    roi = get_roi(
        place_name=region_cfg["region"]["place_name"],
        fallback_coords=region_cfg["region"]["fallback_polygon"],
    )

    # ---- Load building height dataset
    logger.info("Loading building height dataset from GEE")
    height_image = load_temporal_building_height(
        dataset_id=export_cfg["dataset"]["collection_id"],
        year=export_cfg["dataset"]["year"],
        roi=roi,
        height_band=export_cfg["dataset"]["height_band"],
        presence_band=export_cfg["dataset"]["confidence_band"],
        confidence_threshold=export_cfg["dataset"]["confidence_threshold"],
    )

    # ---- OSM building footprints
    logger.info("Downloading building footprints from OSM")
    buildings_gdf = get_osm_building_footprints(
        place_name=region_cfg["region"]["place_name"],
    )

    buildings_fc = gdf_to_ee_feature_collection(buildings_gdf)

        # ---- Zonal statistics
    logger.info("Computing mean building height per footprint")
    reduced_fc = extract_mean_height_per_building(
        buildings_fc=buildings_fc,
        height_image=height_image,
        scale=export_cfg["dataset"]["scale_meters"],
    )

    # ---- Export
    meta = {
        **export_cfg["export"]["metadata"],
        "region_slug": region_cfg["region"]["region_slug"],
    }

    filename = export_cfg["export"]["filename_pattern"].format(**meta)

    logger.info(f"Exporting {filename} to Google Drive")

    export_feature_collection_to_drive(
        fc=reduced_fc,
        description=filename,
        folder=export_cfg["export"]["drive_folder"],
        filename_prefix=filename,
        file_format=export_cfg["export"]["file_format"],
    )

    logger.info("Building height export pipeline finished successfully")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True)
    args = parser.parse_args()

    main(args.region)