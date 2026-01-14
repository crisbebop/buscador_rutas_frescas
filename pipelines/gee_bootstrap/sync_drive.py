import os
import yaml
import argparse
import logging
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

from cool_routes.utils.load_yaml import load_yaml
from cool_routes.utils.log_config import configure_logging


SCOPES = ["https://www.googleapis.com/auth/drive"]


# =================================================
# Configuration
# =================================================

BASE_DIR = Path(__file__).resolve().parents[2]

CONFIG_DIR = BASE_DIR / "config" / "sync_drive"


def authenticate(credentials_path: str, token_path: str):
    creds = None

    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except RefreshError:
            os.remove(token_path)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                os.remove(token_path)
                creds = None

        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return creds


def get_drive_service(creds):
    return build("drive", "v3", credentials=creds)

def list_drive_files(service, query: str):
    """
    List files in Google Drive using a raw query.
    """
    files = []
    page_token = None

    while True:
        response = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, size, modifiedTime)",
            pageToken=page_token,
        ).execute()

        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return files

def filter_files(
    files: list[dict],
    *,
    extensions: list[str] | None = None,
    name_contains: list[str] | None = None,
):
    """
    Filter Drive files by extension and/or substring in name.
    """
    filtered = files

    if extensions:
        filtered = [
            f for f in filtered
            if any(f["name"].lower().endswith(ext.lower()) for ext in extensions)
        ]

    if name_contains:
        filtered = [
            f for f in filtered 
            if any(n.lower() in f["name"].lower() for n in name_contains)
        ]

    return filtered

def download_drive_file(
    service,
    *,
    file_id: str,
    filename: str,
    target_dir: Path,
):
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename

    request = service.files().get_media(fileId=file_id)
    with open(target_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    return target_path

# =================================================
# Pipeline
# =================================================

def main():
    # ---- Logging
    configure_logging("INFO")
    logger = logging.getLogger(__name__)

    # ---- Load config
    config = load_yaml(CONFIG_DIR / "sync_drive.yaml")

    # ---- Auth & service
    creds = authenticate(
        config["auth"]["credentials_path"],
        config["auth"]["token_path"],
    )
    service = get_drive_service(creds)

    # ---- Build Drive query (no folder dependency)
    query = "trashed = false"

    logger.info("Listing files from Google Drive")
    files = list_drive_files(service, query)

    # ---- Apply filters
    files = filter_files(
        files,
        extensions=config["google_drive"].get("file_extensions"),
        name_contains=config["google_drive"].get("name_contains"),
    )

    target_dir = Path(config["local"]["target_dir"])
    overwrite = config["sync"]["overwrite"]

    logger.info(f"Sincronizando {len(files)} archivos desde Drive")

    for f in files:
        local_file = target_dir / f["name"]

        if local_file.exists() and not overwrite:
            logger.info(f"Skipping {f['name']} (already exists)")
            continue

        logger.info(f"Downloading {f['name']}")
        download_drive_file(
            service,
            file_id=f["id"],
            filename=f["name"],
            target_dir=target_dir,
        )


if __name__ == "__main__":
    main()

