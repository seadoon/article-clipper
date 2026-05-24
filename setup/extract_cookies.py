"""
Step 1: note.com の Firefox セッション Cookie を抽出する。

使い方:
  1. Firefox で note.com にログインした状態で Firefox を終了する
  2. python setup/extract_cookies.py を実行
  3. 出力された JSON 文字列を GitHub Secrets の NOTE_COOKIES に貼り付ける
"""

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
    # 最終更新日時が最も新しいものを選ぶ
    return max(candidates, key=lambda p: p.stat().st_mtime)


def extract_cookies(domain: str = "note.com") -> dict:
    profile = find_firefox_profile()
    print(f"プロファイル: {profile}")

    cookies_db = profile / "cookies.sqlite"
    if not cookies_db.exists():
        raise FileNotFoundError(f"cookies.sqlite が見つかりません: {cookies_db}")

    # Firefox が書き込み中の可能性があるため一時コピーを使う
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
    print("note.com の Cookie を Firefox から抽出します...")
    print("※ Firefox はあらかじめ終了しておいてください\n")

    try:
        cookies = extract_cookies()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return

    if not cookies:
        print("❌ note.com の Cookie が見つかりません。Firefox で note.com にログインしてから再試行してください。")
        return

    print(f"✅ {len(cookies)} 件の Cookie を取得しました\n")

    cookies_json = json.dumps(cookies)

    print("=" * 60)
    print("以下を GitHub Secrets の NOTE_COOKIES にコピーしてください:")
    print("=" * 60)
    print(cookies_json)
    print("=" * 60)

    # ローカル確認用に保存（GitHub に push しないこと）
    out = Path("note_cookies.json")
    out.write_text(json.dumps(cookies, indent=2, ensure_ascii=False))
    print(f"\nローカル確認用: {out.resolve()} （GitHub には push しないこと）")


if __name__ == "__main__":
    main()
