import json
import logging
import os
import re
import time
from datetime import datetime

import feedparser
import html2text
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://note.com/",
}

# note.com のコンテンツ div を見つけるためのセレクタ（優先順）
CONTENT_SELECTORS = [
    {"class": re.compile(r"textnote[_-]body", re.I)},
    {"class": re.compile(r"note[_-]body", re.I)},
    {"class": re.compile(r"p-article__body", re.I)},
    {"class": re.compile(r"article[_-]body", re.I)},
]

# ペイウォール存在のインジケータ
PAYWALL_SELECTORS = [
    {"class": re.compile(r"purchase", re.I)},
    {"class": re.compile(r"paywall", re.I)},
    {"class": re.compile(r"limited[-_]free", re.I)},
    {"class": re.compile(r"p-article-purchase", re.I)},
]


def load_cookies() -> dict:
    raw = os.environ.get("NOTE_COOKIES", "{}")
    return json.loads(raw)


def fetch_rss(username: str) :
    """RSS から新着記事のメタデータ一覧を取得する"""
    url = f"https://note.com/{username}/rss"
    feed = feedparser.parse(url)
    return [
        {
            "url": entry.link,
            "title": entry.title,
            "username": username,
        }
        for entry in feed.entries
    ]


def fetch_article(url: str, cookies: dict) :
    """
    1記事を取得して辞書で返す。
    ペイウォール（未購入）は {"paywalled": True, "title": ..., "url": ...}
    取得失敗は None
    """
    session = requests.Session()
    session.cookies.update(cookies)

    try:
        resp = session.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"fetch failed {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    # ----- メタデータ -----
    og_title = soup.find("meta", property="og:title")
    title = og_title["content"] if og_title else (
        soup.find("h1").get_text(strip=True) if soup.find("h1") else "Untitled"
    )

    pub_meta = soup.find("meta", property="article:published_time")
    if pub_meta:
        try:
            published = datetime.fromisoformat(
                pub_meta["content"].replace("Z", "+00:00")
            ).strftime("%Y-%m-%d")
        except ValueError:
            published = datetime.now().strftime("%Y-%m-%d")
    else:
        time_tag = soup.find("time", {"datetime": True})
        published = (
            time_tag["datetime"][:10] if time_tag else datetime.now().strftime("%Y-%m-%d")
        )

    author_meta = soup.find("meta", {"name": "author"})
    author_display = author_meta["content"] if author_meta else ""

    # ----- メンバーシップ判定 -----
    is_membership = bool(
        soup.find(attrs={"class": re.compile(r"membership", re.I)})
        or soup.find(attrs={"data-note-type": "membership"})
    )

    # ----- コンテンツ抽出 -----
    content_div = None
    for selector in CONTENT_SELECTORS:
        content_div = soup.find("div", selector)
        if content_div:
            break
    if content_div is None:
        content_div = soup.find("article")

    if content_div is None:
        logger.warning(f"no content div found: {url}")
        return None

    content_text = content_div.get_text(strip=True)

    # ----- ペイウォール判定 -----
    # ペイウォール要素があればスキップ（購入済み記事には paywall 要素が出ない）
    has_paywall_el = any(soup.find(attrs=sel) for sel in PAYWALL_SELECTORS)
    if has_paywall_el:
        logger.info(f"paywalled (not purchased): {title}")
        return {"paywalled": True, "title": title, "url": url}

    # ----- HTML → Markdown -----
    h2t = html2text.HTML2Text()
    h2t.ignore_links = False
    h2t.body_width = 0
    h2t.ignore_images = False
    content_md = h2t.handle(str(content_div))

    return {
        "paywalled": False,
        "title": title,
        "url": url,
        "published": published,
        "author_display": author_display,
        "is_membership": is_membership,
        "content_md": content_md,
    }
