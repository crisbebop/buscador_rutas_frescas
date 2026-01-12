"""
Pipeline: Export LST from Google Earth Engine.

Responsibility:
- Orchestrate LST extraction for a Region of Interest
- Export LST raster to Google Drive

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
    load_landsat8_lst_collection,
    scale_to_celsius,
    apply_landsat8_cloud_mask,
    validate_image_collection,
    build_lst_composite,
    export_image_to_drive
)

# =================================================
# Configuration
# =================================================

BASE_DIR = Path(__file__).resolve().parents[2]

CONFIG_DIR = BASE_DIR / "config" / "gee"
REGIONS_DIR = BASE_DIR / "config" / "regions"

# =================================================
# Pipeline
# =================================================

def main(region_slug):
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
    export_cfg = load_yaml(CONFIG_DIR / "export_lst.yaml")
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

    # ---- LST
    lst_config = export_cfg["dataset"]

    collection = load_landsat8_lst_collection(
    start_date=lst_config["start_date"],
    end_date=lst_config["end_date"],
    roi=roi,
    )

    processed = collection.map(scale_to_celsius)
    if lst_config["cloud_mask"]["enabled"] is True:
        logger.info("Applying cloud mask to Landsat 8 collection")
        processed = processed.map(apply_landsat8_cloud_mask)
    else:
        logger.info("Cloud mask disabled, skipping masking step")

    validate_image_collection(
        processed,
        context="Landsat 8 LST after cloud masking",
    )

    lst_image = build_lst_composite(
        collection=processed,
        roi=roi,
        reducer=lst_config["reducer"],
    )

    # ---- Export
    meta = {
        **export_cfg["export"]["metadata"],
        "region_slug": region_cfg["region"]["region_slug"],
    }

    filename = export_cfg["export"]["filename_pattern"].format(**meta)

    logger.info(f"Exporting {filename} to Google Drive")

    export_image_to_drive(
        image=lst_image,
        description=filename,
        folder=export_cfg["export"].get("drive_folder"),
        filename_prefix=filename,
        region=roi,
        scale=export_cfg["export"]["scale_meters"],
        crs=export_cfg["export"].get("crs", "EPSG:4326"),
    )

    logger.info("lst_image export task submitted successfully")
    logger.info("Check Google Earth Engine Tasks and Google Drive")


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True)
    args = parser.parse_args()

    main(args.region)