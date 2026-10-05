import json
import logging
import os
import re
from datetime import datetime

import feedparser
import html2text
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/",
}

def load_cookies() -> dict:
    raw = os.environ.get("PLATFORM_COOKIES", os.environ.get("NOTE_COOKIES", "{}"))
    return json.loads(raw)


def fetch_rss(rss_url: str):
    feed = feedparser.parse(rss_url)
    return [
        {
            "url": entry.link,
            "title": entry.title,
        }
        for entry in feed.entries
    ]


def fetch_article(url: str, cookies: dict):
    """note の記事を API から取得する。

    note.com は 2026-10 にサーバーレンダリングをやめ、HTML の本文 div が空で
    返るようになった。同時に有料ブロックの要素は購読者にも描画されるため、
    DOM からの本文抽出・ペイウォール判定はどちらも成立しない。
    購読可否は API の can_read を正とする。
    """
    m = re.search(r"/n/(n[0-9a-z]+)", url)
    if not m:
        logger.error(f"note key not found in url: {url}")
        return None

    session = requests.Session()
    session.cookies.update(cookies)

    try:
        resp = session.get(
            f"https://note.com/api/v3/notes/{m.group(1)}",
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
    except (requests.RequestException, ValueError, KeyError) as e:
        logger.error(f"fetch failed {url}: {e}")
        return None

    title = f"{data['name']}｜{(data.get('user') or {}).get('nickname', '')}".rstrip("｜")

    if not data.get("can_read"):
        logger.info(f"paywalled: {title}")
        return {"paywalled": True, "title": title, "url": url}

    body = data.get("body")
    if not body:
        logger.warning(f"can_read but empty body: {url}")
        return None

    h2t = html2text.HTML2Text()
    h2t.ignore_links = False
    h2t.body_width = 0
    h2t.ignore_images = False
    content_md = h2t.handle(body)

    published = (data.get("publish_at") or data.get("created_at") or "")[:10]
    if not published:
        published = datetime.now().strftime("%Y-%m-%d")

    return {
        "paywalled": False,
        "title": title,
        "url": url,
        "published": published,
        "author_display": "",
        "content_md": content_md,
    }
