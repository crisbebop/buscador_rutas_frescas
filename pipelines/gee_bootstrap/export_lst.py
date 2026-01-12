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
CONFIG_PATH = BASE_DIR / "config" / "gee" / "export_lst.yaml"


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


# =================================================
# Pipeline
# =================================================

def main() -> None:
    config = load_config(CONFIG_PATH)
    setup_logging(config.get("log_level", "INFO"))
    logger = logging.getLogger("export_lst")

    logger.info("Starting LST export pipeline")

    # ---- Initialize GEE
    init_gee(project_id=config["gee"]["project_id"])

    # ---- ROI
    logger.info("Resolving region of interest (ROI)")
    roi = get_roi(
        place_name=config["region"]["place_name"],
        fallback_coords=config["region"]["fallback_polygon"],
    )

    # ---- LST
    lst_config = config["dataset"]

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
        reducer=config["dataset"]["reducer"],
    )

    # ---- Export

    export_cfg = config["export"]

    # Extraer metadatos
    meta = config['export']['metadata']
    meta['region_slug'] = config['region']['region_slug']

    # Construir el nombre usando el patrón
    file_name_prefix = config['export']['filename_pattern'].format(**meta)

    export_image_to_drive(
        image=lst_image,
        description=file_name_prefix,
        folder=export_cfg["drive_folder"],
        filename_prefix=file_name_prefix,
        region=roi,
        scale=export_cfg["scale_meters"],
        crs=export_cfg.get("crs", "EPSG:4326"),
    )

    logger.info("lst_image export task submitted successfully")
    logger.info("Check Google Earth Engine Tasks and Google Drive")


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    main()