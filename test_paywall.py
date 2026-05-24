"""
ペイウォール判定テスト。
各著者のRSSから最新2件を取得して判定結果を表示する。
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fetcher import fetch_article, fetch_rss, load_cookies

AUTHORS = ["abctrader", "paul1211", "so_nandachem"]
SAMPLE_PER_AUTHOR = 2

cookies_path = Path(__file__).parent / "cookies.json"
cookies = json.loads(cookies_path.read_text(encoding="utf-8")) if cookies_path.exists() else load_cookies()


def test_author(username):
    print(f"\n{'='*55}")
    print(f"  {username}")
    print(f"{'='*55}")
    items = fetch_rss(username)
    if not items:
        print("  ❌ RSS取得失敗")
        return

    for item in items[:SAMPLE_PER_AUTHOR]:
        url = item["url"]
        print(f"\n  URL: {url}")
        result = fetch_article(url, cookies)
        time.sleep(1.5)

        if result is None:
            print("  → ❌ 取得失敗 (None)")
            continue

        if result["paywalled"]:
            print(f"  → 🔒 ペイウォール (未購入): {result['title']}")
        else:
            body_len = len(result.get("content_md", ""))
            print(f"  → ✅ 取得OK: {result['title']}")
            print(f"     本文: {body_len} 文字 / 公開日: {result.get('published')}")


for author in AUTHORS:
    test_author(author)

print("\n\nテスト完了")
