"""
Pipeline: Export NDVI from Google Earth Engine.

Responsibility:
- Orchestrate NDVI extraction for a Region of Interest
- Export NDVI raster to Google Drive

Domain logic lives in: cool_routes.ingest.gee
"""

from pathlib import Path
import logging
import yaml

from cool_routes.ingest.gee import (
    init_gee,
    get_roi,
    load_ndvi,
    export_image_to_drive
)

# =================================================
# Configuration
# =================================================

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "config" / "gee" / "export_ndvi.yaml"


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
    logger = logging.getLogger("export_ndvi")

    logger.info("Starting NDVI export pipeline")

    # ---- Initialize GEE
    init_gee(project_id=config["gee"]["project_id"])

    # ---- ROI
    logger.info("Resolving region of interest (ROI)")
    roi = get_roi(
        place_name=config["region"]["place_name"],
        fallback_coords=config["region"]["fallback_polygon"],
    )

    # ---- NDVI
    ndvi_config = config["dataset"]

    ndvi_img = load_ndvi(
        start_date= ndvi_config["start_date"],
        end_date= ndvi_config["end_date"],
        roi= roi,
        cloud_percentage= ndvi_config["cloud_mask"]["threshold"],
        s2_colection= ndvi_config["collection_id"],
    )

    # ---- Export

    export_cfg = config["export"]

    # 1. Extraer metadatos
    meta = config['export']['metadata']
    meta['region_slug'] = config['region']['region_slug'] # Agregar el slug de la region

    # 2. Construir el nombre usando el patrón
    file_name_prefix = config['export']['filename_pattern'].format(**meta)

    export_image_to_drive(
        image=ndvi_img,
        description=file_name_prefix,
        folder=export_cfg["drive_folder"],
        filename_prefix=file_name_prefix,
        region=roi,
        scale=export_cfg["scale_meters"],
        crs=export_cfg.get("crs", "EPSG:4326"),
    )

    logger.info("NDVI export task submitted successfully")
    logger.info("Check Google Earth Engine Tasks and Google Drive")


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    main()