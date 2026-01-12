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


SCOPES = ["https://www.googleapis.com/auth/drive"]

# ----------------------------------
# Utils
# ----------------------------------

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sync files from Google Drive to local storage"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to sync configuration YAML"
    )
    return parser.parse_args()


# def load_config(path: str) -> dict:
#     with open(path, "r") as f:
#         return yaml.safe_load(f)


def authenticate(credentials_path: str, token_path: str):
    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return creds


def get_drive_service(creds):
    return build("drive", "v3", credentials=creds)


def find_folder_id(service, folder_name: str) -> str:
    query = (
        f"name = '{folder_name}' and "
        f"mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )

    response = service.files().list(q=query, fields="files(id, name)").execute()
    folders = response.get("files", [])

    if not folders:
        raise RuntimeError(f"Folder '{folder_name}' not found in Drive")

    return folders[0]["id"]


def list_files(service, folder_id: str, extensions: list[str]):
    query = f"'{folder_id}' in parents and trashed = false"
    response = service.files().list(
        q=query, fields="files(id, name, size)"
    ).execute()

    files = response.get("files", [])
    return [
        f for f in files if any(f["name"].endswith(ext) for ext in extensions)
    ]


def download_file(service, file_id: str, filename: str, target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename

    request = service.files().get_media(fileId=file_id)
    with open(target_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    print(f"✔ Downloaded {filename}")



def main():
    args = parse_args()
    config = load_config(args.config)

    logging.basicConfig(
        level=config["sync"].get("log_level", "INFO"),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

# def main():
#     config = load_config("config/sync_drive.yaml")

    creds = authenticate(
        config["auth"]["credentials_path"],
        config["auth"]["token_path"],
    )

    service = get_drive_service(creds)

    folder_id = find_folder_id(
        service, config["google_drive"]["folder_name"]
    )

    files = list_files(
        service,
        folder_id,
        config["google_drive"]["file_extensions"],
    )

    target_dir = Path(config["local"]["target_dir"])

    for f in files:
        local_file = target_dir / f["name"]
        if local_file.exists() and not config["sync"]["overwrite"]:
            print(f"↷ Skipping {f['name']} (already exists)")
            continue

        download_file(service, f["id"], f["name"], target_dir)


if __name__ == "__main__":
    main()
