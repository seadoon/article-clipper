"""
Step 3: Google Drive のフォルダ ID を探索して config/folder_ids.json に保存する。

使い方:
  1. python setup/init_auth.py を実行済みで google_token.json がある状態で
  2. python setup/init_drive_paths.py を実行
  3. config/folder_ids.json が生成されたら git commit して push する
"""

import json
import sys
from pathlib import Path

# src/ 内の config.py を import できるようにパスを通す
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import NOTE_AUTHORS
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def find_folder(service, name: str, parent_id: str):
    """parent_id の直下から name のフォルダを探して ID を返す。なければ None"""
    q = (
        f"name='{name}' "
        f"and '{parent_id}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )
    results = service.files().list(q=q, fields="files(id, name)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def navigate_path(service, path: str) -> str:
    """
    スラッシュ区切りのパスを Drive root から辿って末端フォルダの ID を返す。
    例: "obsidian_sync/Investment/raw/ABC Trader/記事"
    """
    parts = [p for p in path.split("/") if p]
    parent = "root"
    for part in parts:
        folder_id = find_folder(service, part, parent)
        if folder_id is None:
            raise ValueError(
                f"フォルダが見つかりません: '{part}'\n"
                f"  フルパス: {path}\n"
                f"  親フォルダ ID: {parent}\n"
                f"  → Google Drive でこのフォルダが存在するか確認してください"
            )
        parent = folder_id
    return parent


def collect_all_paths() -> set[str]:
    """config から探索が必要な全パスを集める"""
    paths: set[str] = set()
    for cfg in NOTE_AUTHORS.values():
        for key in ("drive_path", "drive_path_membership", "drive_path_article"):
            if key in cfg:
                paths.add(cfg[key])
    return paths


def main() -> None:
    token_file = Path(__file__).parent / "google_token.json"
    if not token_file.exists():
        print("❌ google_token.json が見つかりません。先に init_auth.py を実行してください。")
        return

    creds = Credentials.from_authorized_user_info(json.loads(token_file.read_text()))
    service = build("drive", "v3", credentials=creds)

    paths = collect_all_paths()
    print(f"{len(paths)} 件のフォルダを探索します...\n")

    folder_ids: dict[str, str] = {}
    failed = 0

    for path in sorted(paths):
        print(f"  {path}")
        try:
            fid = navigate_path(service, path)
            folder_ids[path] = fid
            print(f"  ✅ {fid}\n")
        except ValueError as e:
            print(f"  ❌ {e}\n")
            failed += 1

    # 保存
    out = Path(__file__).parent.parent / "config" / "folder_ids.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(folder_ids, indent=2, ensure_ascii=False))

    print(f"✅ config/folder_ids.json に {len(folder_ids)} 件保存しました")
    if failed:
        print(f"⚠️  {failed} 件のフォルダが見つかりませんでした。上記エラーを確認してください。")
    print("\n次のステップ: git add config/folder_ids.json && git commit && git push")


if __name__ == "__main__":
    main()
