"""
メインエントリーポイント。
GitHub Actions から呼ばれる。
"""

import json
import logging
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from config import NOTE_AUTHORS
from converter import make_frontmatter, safe_filename
from gdrive import get_drive_service, load_folder_ids, upload_markdown
from note_fetcher import fetch_article, fetch_rss, load_cookies

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

CLIPPED_JSON = Path(__file__).parent.parent / "clipped.json"


def normalize_url(url: str) -> str:
    """クエリパラメータ・フラグメントを除いたクリーンな URL を返す"""
    p = urlparse(url)
    return p._replace(query="", fragment="").geturl()


def load_clipped() -> dict:
    if CLIPPED_JSON.exists():
        data = json.loads(CLIPPED_JSON.read_text(encoding="utf-8"))
        data["note"] = [normalize_url(u) for u in data["note"]]
        return data
    return {"note": []}


def save_clipped(clipped: dict) -> None:
    CLIPPED_JSON.write_text(
        json.dumps(clipped, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def clip_note(drive, folder_ids: dict, clipped: dict) -> int:
    cookies = load_cookies()
    count = 0

    for username, cfg in NOTE_AUTHORS.items():
        logger.info(f"[note] checking RSS: {username}")
        rss_items = fetch_rss(username)

        for item in rss_items:
            url = normalize_url(item["url"])
            if url in clipped["note"]:
                continue

            logger.info(f"[note] fetching: {url}")
            article = fetch_article(url, cookies)
            time.sleep(1.5)

            if article is None:
                logger.warning(f"[note] fetch failed: {url}")
                continue

            if article["paywalled"]:
                logger.info(f"[note] skip (not purchased): {article['title']}")
                clipped["note"].append(url)
                continue

            # パウロだけメンバーシップ / 記事で振り分け
            if username == "paul1211":
                drive_path = (
                    cfg["drive_path_membership"]
                    if article["is_membership"]
                    else cfg["drive_path_article"]
                )
            else:
                drive_path = cfg["drive_path"]

            folder_id = folder_ids.get(drive_path)
            if not folder_id:
                logger.error(f"[note] folder_id not found for: {drive_path}")
                continue

            md = make_frontmatter(
                title=article["title"],
                source_url=url,
                obsidian_link=cfg["obsidian_link"],
                published_date=article["published"],
            ) + article["content_md"]

            fname = safe_filename(article["title"], article["author_display"])
            uploaded = upload_markdown(drive, md, fname, folder_id)
            clipped["note"].append(url)
            if uploaded:
                count += 1

    return count


def main() -> None:
    logger.info("=== note-clipper start ===")

    clipped = load_clipped()
    folder_ids = load_folder_ids()
    drive = get_drive_service()

    note_count = clip_note(drive, folder_ids, clipped)

    save_clipped(clipped)
    logger.info(f"=== done: {note_count} articles clipped ===")


if __name__ == "__main__":
    main()
