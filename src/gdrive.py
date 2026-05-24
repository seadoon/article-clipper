import json
import logging
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

logger = logging.getLogger(__name__)

_FOLDER_IDS: dict | None = None


def get_drive_service():
    creds = Credentials.from_authorized_user_info(
        json.loads(os.environ["GOOGLE_TOKEN"])
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("drive", "v3", credentials=creds)


def load_folder_ids() -> dict:
    global _FOLDER_IDS
    if _FOLDER_IDS is None:
        ids_path = Path(__file__).parent.parent / "config" / "folder_ids.json"
        with open(ids_path, encoding="utf-8") as f:
            _FOLDER_IDS = json.load(f)
    return _FOLDER_IDS


def upload_markdown(service, content: str, filename: str, folder_id: str) -> bool:
    """
    Google Drive の folder_id 内に markdown ファイルをアップロードする。
    同名ファイルが既にあればスキップして False を返す。
    成功したら True を返す。
    """
    # 同名ファイルが既にあるか確認
    q = (
        f"name='{filename}' and '{folder_id}' in parents "
        f"and trashed=false"
    )
    existing = (
        service.files().list(q=q, fields="files(id)").execute().get("files", [])
    )
    if existing:
        logger.debug(f"already exists, skip: {filename}")
        return False

    media = MediaInMemoryUpload(
        content.encode("utf-8"),
        mimetype="text/markdown",
        resumable=False,
    )
    service.files().create(
        body={"name": filename, "parents": [folder_id]},
        media_body=media,
        fields="id",
    ).execute()
    logger.info(f"uploaded: {filename}")
    return True
