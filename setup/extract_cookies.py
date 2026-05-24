"""
Step 1: Firefox のセッション Cookie を抽出する。

使い方:
  1. Firefox でログインした状態で Firefox を終了する
  2. python setup/extract_cookies.py --domain <対象ドメイン> を実行
  3. 出力された JSON 文字列を GitHub Secrets の PLATFORM_COOKIES に貼り付ける
"""

import argparse
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path


def find_firefox_profile() -> Path:
    profiles_root = Path.home() / "Library/Application Support/Firefox/Profiles"
    candidates = (
        sorted(profiles_root.glob("*.default-release"))
        + sorted(profiles_root.glob("*.default"))
    )
    if not candidates:
        raise FileNotFoundError(
            "Firefox プロファイルが見つかりません。"
            f"確認先: {profiles_root}"
        )
    return max(candidates, key=lambda p: p.stat().st_mtime)


def extract_cookies(domain: str) -> dict:
    profile = find_firefox_profile()
    print(f"プロファイル: {profile}")

    cookies_db = profile / "cookies.sqlite"
    if not cookies_db.exists():
        raise FileNotFoundError(f"cookies.sqlite が見つかりません: {cookies_db}")

    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        shutil.copy2(cookies_db, tmp_path)
        conn = sqlite3.connect(tmp_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, value FROM moz_cookies WHERE host LIKE ?",
            (f"%{domain}%",),
        )
        cookies = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
    finally:
        tmp_path.unlink(missing_ok=True)

    return cookies


def main() -> None:
    parser = argparse.ArgumentParser(description="Firefox から Cookie を抽出する")
    parser.add_argument("--domain", required=True, help="対象ドメイン（例: example.com）")
    args = parser.parse_args()

    print(f"Cookie を Firefox から抽出します（ドメイン: {args.domain}）...")
    print("※ Firefox はあらかじめ終了しておいてください\n")

    try:
        cookies = extract_cookies(args.domain)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return

    if not cookies:
        print(f"❌ {args.domain} の Cookie が見つかりません。Firefox でログインしてから再試行してください。")
        return

    print(f"✅ {len(cookies)} 件の Cookie を取得しました\n")

    cookies_json = json.dumps(cookies)

    print("=" * 60)
    print("以下を GitHub Secrets の PLATFORM_COOKIES にコピーしてください:")
    print("=" * 60)
    print(cookies_json)
    print("=" * 60)

    out = Path("cookies.json")
    out.write_text(json.dumps(cookies, indent=2, ensure_ascii=False))
    print(f"\nローカル確認用: {out.resolve()} （GitHub には push しないこと）")


if __name__ == "__main__":
    main()
