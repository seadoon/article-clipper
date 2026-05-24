import base64
import json
import logging
import os
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

import html2text
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def get_gmail_service():
    creds = Credentials.from_authorized_user_info(
        json.loads(os.environ["GOOGLE_TOKEN"])
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def _decode_part(payload: dict) -> str:
    """メール payload から HTML or プレーンテキストを再帰的に取り出す"""
    mime = payload.get("mimeType", "")

    if mime in ("text/html", "text/plain"):
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = _decode_part(part)
        if result:
            return result

    return ""


def _html_to_md(html: str) -> str:
    h2t = html2text.HTML2Text()
    h2t.ignore_links = False
    h2t.body_width = 0
    return h2t.handle(html)


def fetch_new_emails(
    service,
    already_processed: list[str],
    mag2_id: str,
    gmail_query: str,
) -> list[dict]:
    """
    まぐまぐのメルマガメールを取得して返す。
    already_processed に含まれる message ID はスキップする。
    """
    try:
        results = service.users().messages().list(
            userId="me", q=gmail_query, maxResults=50
        ).execute()
    except Exception as e:
        logger.error(f"Gmail list error: {e}")
        return []

    messages = results.get("messages", [])
    articles = []

    for ref in messages:
        msg_id = ref["id"]
        if msg_id in already_processed:
            continue

        try:
            msg = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()
        except Exception as e:
            logger.error(f"Gmail get error {msg_id}: {e}")
            continue

        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        subject = headers.get("Subject", "No Subject")
        date_str = headers.get("Date", "")

        try:
            published = parsedate_to_datetime(date_str).strftime("%Y-%m-%d")
        except Exception:
            published = datetime.now().strftime("%Y-%m-%d")

        body_raw = _decode_part(msg["payload"])
        if not body_raw:
            logger.warning(f"empty body: {msg_id} subject={subject}")
            continue

        # HTML か plain text かを判断して Markdown に変換
        if re.search(r"<html", body_raw, re.I):
            content_md = _html_to_md(body_raw)
        else:
            content_md = body_raw  # already plain text

        articles.append(
            {
                "msg_id": msg_id,
                "title": subject,
                "published": published,
                "content_md": content_md,
            }
        )

    return articles
