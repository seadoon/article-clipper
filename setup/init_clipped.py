"""
Step 4: 既存の Obsidian ファイルをスキャンして clipped.json を初期化する。

既にクリップ済みの記事・メルマガを重複して保存しないようにするための初回セットアップ。

使い方:
  python setup/init_clipped.py \
    --vault "/Users/seado/Library/CloudStorage/GoogleDrive-xxx/マイドライブ/obsidian_sync/Investment"
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ──────────────────────────────────────────
# note.com: raw/ をスキャンして source URL を収集
# ──────────────────────────────────────────

def extract_source_url(md_file: Path) -> str | None:
    """frontmatter の source: フィールドから URL を取り出す"""
    try:
        text = md_file.read_text(encoding="utf-8")
    except Exception:
        return None
    m = re.search(r'^source:\s*["\']?([^"\':\n][^\n]*?)["\']?\s*$', text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def scan_note_urls(vault_path: Path) -> list[str]:
    raw_dir = vault_path / "raw"
    if not raw_dir.exists():
        print(f"  ❌ raw/ が見つかりません: {raw_dir}")
        return []

    urls = []
    for md_file in raw_dir.rglob("*.md"):
        url = extract_source_url(md_file)
        if url and "note.com" in url:
            urls.append(url)
            print(f"  {url}")

    return urls


# ──────────────────────────────────────────
# Gmail: まぐまぐの既存メールを全件 processed 扱いにする
# ──────────────────────────────────────────

def fetch_all_mag2_message_ids(token_path: Path, mag2_id: str) -> list[str]:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_info(
        json.loads(token_path.read_text())
    )
    service = build("gmail", "v1", credentials=creds)

    query = f"from:{mag2_id}@mag2.com"
    msg_ids: list[str] = []
    page_token = None

    while True:
        kwargs: dict = {"userId": "me", "q": query, "maxResults": 100}
        if page_token:
            kwargs["pageToken"] = page_token

        result = service.users().messages().list(**kwargs).execute()
        for m in result.get("messages", []):
            msg_ids.append(m["id"])
            print(f"  {m['id']}")

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return msg_ids


# ──────────────────────────────────────────
# メイン
# ──────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="既存 Obsidian コンテンツを clipped.json に登録して重複防止"
    )
    parser.add_argument("--vault", required=True, help="Obsidian vault のフルパス")
    args = parser.parse_args()

    vault_path = Path(args.vault).expanduser()
    clipped_json = Path(__file__).parent.parent / "clipped.json"

    print(f"vault: {vault_path}\n")

    # ── note.com ──
    print("=" * 50)
    print("[1/2] note.com の既存 URL をスキャン中...")
    print("=" * 50)
    note_urls = scan_note_urls(vault_path)
    print(f"\n→ {len(note_urls)} 件検出\n")

    # ── Gmail ──
    print("=" * 50)
    print("[2/2] Gmail: まぐまぐの既存メールを検索中...")
    print("=" * 50)

    token_path = Path(__file__).parent / "google_token.json"
    gmail_ids: list[str] = []

    if not token_path.exists():
        print("  ⚠️  google_token.json が見つかりません")
        print("  → init_auth.py を先に実行してください")
        print("  → Gmail 側の重複防止はスキップ（初回実行時に既存メルマガが再クリップされる可能性）")
    else:
        try:
            from config import MAILMAG_AUTHORS
            for cfg in MAILMAG_AUTHORS.values():
                print(f"  {cfg['display_name']} (ID: {cfg['mag2_id']})")
                ids = fetch_all_mag2_message_ids(token_path, cfg["mag2_id"])
                gmail_ids.extend(ids)
                print(f"  → {len(ids)} 件\n")
        except Exception as e:
            print(f"  ❌ Gmail API エラー: {e}")

    # ── 書き込み ──
    clipped = {
        "note": sorted(set(note_urls)),
        "gmail": sorted(set(gmail_ids)),
    }

    clipped_json.write_text(
        json.dumps(clipped, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("=" * 50)
    print(f"✅ clipped.json を更新しました")
    print(f"   note:  {len(clipped['note'])} 件")
    print(f"   gmail: {len(clipped['gmail'])} 件")
    print()
    print("次のステップ:")
    print("  git add clipped.json && git commit -m 'init: mark existing content as clipped' && git push")


if __name__ == "__main__":
    main()
