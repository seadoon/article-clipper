"""
Step 2: Google 認証（Gmail + Drive 両方）。

使い方:
  1. Google Cloud Console で OAuth 2.0 クライアント ID (デスクトップアプリ) を作成してダウンロード
  2. ダウンロードした JSON を client_secret.json としてこのディレクトリに置く
  3. python setup/init_auth.py を実行 → ブラウザが開くのでログイン
  4. 出力された JSON を GitHub Secrets の GOOGLE_TOKEN に貼り付ける

必要なスコープ:
  - gmail.readonly  (メルマガ受信)
  - drive           (vault への書き込み)
"""

import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive",
]


def main() -> None:
    secret_file = Path("client_secret.json")
    if not secret_file.exists():
        print("❌ client_secret.json が見つかりません")
        print()
        print("取得手順:")
        print("  1. https://console.cloud.google.com/ を開く")
        print("  2. プロジェクトを作成（または既存を選択）")
        print("  3. APIs & Services > Enable APIs > Gmail API と Google Drive API を有効化")
        print("  4. APIs & Services > Credentials > + CREATE CREDENTIALS > OAuth client ID")
        print("  5. Application type: Desktop app → CREATE")
        print("  6. ダウンロードして client_secret.json にリネームしてここに置く")
        return

    flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)
    creds = flow.run_local_server(port=0)

    token_data = json.loads(creds.to_json())
    token_json = json.dumps(token_data)

    print("\n✅ 認証成功！\n")
    print("=" * 60)
    print("以下を GitHub Secrets の GOOGLE_TOKEN にコピーしてください:")
    print("=" * 60)
    print(token_json)
    print("=" * 60)

    # ローカル確認用に保存（init_drive_paths.py でも使う）
    out = Path("google_token.json")
    out.write_text(json.dumps(token_data, indent=2))
    print(f"\nローカル確認用: {out.resolve()}")
    print("次のステップ: python setup/init_drive_paths.py を実行")


if __name__ == "__main__":
    main()
