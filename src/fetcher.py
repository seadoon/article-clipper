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
    "Referer": "https://www.google.com/",
}

CONTENT_SELECTORS = [
    {"class": re.compile(r"textnote[_-]body", re.I)},
    {"class": re.compile(r"note[_-]body", re.I)},
    {"class": re.compile(r"p-article__body", re.I)},
    {"class": re.compile(r"article[_-]body", re.I)},
]

PAYWALL_SELECTORS = [
    {"class": re.compile(r"purchase", re.I)},
    {"class": re.compile(r"paywall", re.I)},
    {"class": re.compile(r"limited[-_]free", re.I)},
    {"class": re.compile(r"p-article-purchase", re.I)},
]


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
    session = requests.Session()
    session.cookies.update(cookies)

    try:
        resp = session.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"fetch failed {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

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

    def is_visible_paywall(sel):
        el = soup.find(attrs=sel)
        if el is None:
            return False
        style = el.get("style", "")
        return "display:none" not in style.replace(" ", "")

    has_paywall_el = any(is_visible_paywall(sel) for sel in PAYWALL_SELECTORS)
    if has_paywall_el:
        logger.info(f"paywalled: {title}")
        return {"paywalled": True, "title": title, "url": url}

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
        "content_md": content_md,
    }
