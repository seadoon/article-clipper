"""
Step 4: 既存の Obsidian ファイルをスキャンして clipped.json を初期化する。

既にクリップ済みの記事を重複して保存しないようにするための初回セットアップ。

使い方:
  python setup/init_clipped.py \
    --vault "/Users/xxx/Library/CloudStorage/GoogleDrive-xxx/マイドライブ/obsidian_sync/Investment"
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="既存 Obsidian コンテンツを clipped.json に登録して重複防止"
    )
    parser.add_argument("--vault", required=True, help="Obsidian vault のフルパス")
    args = parser.parse_args()

    vault_path = Path(args.vault).expanduser()
    clipped_json = Path(__file__).parent.parent / "clipped.json"

    print(f"vault: {vault_path}\n")
    print("=" * 50)
    print("raw/ 以下の note.com URL をスキャン中...")
    print("=" * 50)

    note_urls = scan_note_urls(vault_path)

    clipped = {"note": sorted(set(note_urls))}
    clipped_json.write_text(
        json.dumps(clipped, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\n✅ clipped.json を更新しました ({len(clipped['note'])} 件)")
    print()
    print("次のステップ:")
    print("  git add clipped.json && git commit -m 'init: mark existing articles as clipped' && git push")


if __name__ == "__main__":
    main()
