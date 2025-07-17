# セットアップガイド

Claude Conversation Importerの詳細なセットアップ手順を説明します。

## 📋 事前準備

### 必要なもの

1. **Notionアカウント**: ワークスペースの管理者権限
2. **Python環境**: Python 3.8以上
3. **conversations.json**: Claude.aiからエクスポートしたデータ

### Claude.aiからのデータエクスポート

1. [Claude.ai](https://claude.ai) にログイン
2. 設定 → データエクスポート
3. 「会話履歴をエクスポート」を選択
4. `conversations.json`ファイルをダウンロード

## 🔧 Notion Integration作成手順

### Step 1: Integration作成

1. **Notion Integrations ページにアクセス**
   ```
   https://www.notion.so/my-integrations
   ```

2. **「New integration」ボタンをクリック**

3. **Basic Information を入力**
   ```
   Name: Claude Conversation Importer
   Logo: (お好みのアイコンをアップロード)
   Associated workspace: [あなたのワークスペース名]
   ```

4. **Capabilities（権限）を設定**
   ```
   ✅ Read content
   ✅ Update content  
   ✅ Insert content
   ❌ Read user information (不要)
   ❌ Read comments (不要)
   ```

5. **「Submit」ボタンで作成完了**

6. **Integration Token をコピー**
   - 表示された Token をコピー（後で使用）
   - 形式: `secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Step 2: データベース設定

#### 🎯 Option A: 既存データベースを使用

1. **既存の「Claude会話ログ」データベースを開く**

2. **データベースをIntegrationに共有**
   - データベースの右上「Share」ボタンをクリック
   - 検索欄に `Claude Conversation Importer` を入力
   - Integration を選択
   - 権限を「Can edit」に設定
   - 「Invite」ボタンでアクセス権を付与

3. **Database ID を取得**
   ```
   ブラウザのURLから以下の部分をコピー：
   https://www.notion.so/workspace/[DATABASE_ID]?v=view_id
   
   例: https://www.notion.so/myworkspace/723ec38306ac4951b10cacd064f4d8f6?v=123
   → DATABASE_ID: 723ec38306ac4951b10cacd064f4d8f6
   ```

#### 🆕 Option B: 新規データベース作成

1. **親ページを準備**
   - 新しいデータベースを作成したいページを開く
   - URLからPage IDを取得（DATABASE_IDと同じ形式）

2. **ツールで自動作成**
   ```bash
   python -m src.main setup --interactive
   ```
   - 「0. 新規データベースを作成」を選択
   - 親ページIDを入力

## 🔌 環境変数設定

### 対話式セットアップ（推奨）

```bash
# プロジェクトディレクトリで実行
python -m src.main setup --interactive
```

対話式セットアップでは以下が自動で行われます：
- API接続テスト
- データベース一覧表示
- 新規データベース作成（必要に応じて）
- `.env`ファイル自動生成

### 手動セットアップ

1. **環境ファイルをコピー**
   ```bash
   cp .env.example .env
   ```

2. **`.env`ファイルを編集**
   ```env
   # =============================================================================
   # Notion API 設定
   # =============================================================================
   NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   
   # オプション: 新規DB作成時の親ページID
   NOTION_PARENT_PAGE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   
   # =============================================================================
   # アプリケーション設定
   # =============================================================================
   LOG_LEVEL=INFO
   BATCH_SIZE=10
   IMPORT_MODE=update
   AUTO_CREATE_DATABASE=false
   NOTION_API_DELAY=0.1
   MAX_RETRIES=3
   ```

## ✅ 接続テスト

### 基本テスト

```bash
# API接続テスト
python -m src.main test-connection
```

**期待される出力:**
```
🔗 Notion API接続をテストしています...
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 項目                 ┃ 結果     ┃ 詳細                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ API接続              │ ✅ 成功  │                            │
│ データベースアクセス │ ✅ 成功  │                            │
│ データベース構造     │ ✅ 適合  │                            │
└──────────────────────┴──────────┴────────────────────────────┘

データベース情報:
タイトル: Claude会話ログ
プロパティ: タイトル, 日付, トピック, ステータス, 要約, 参考になった度, メッセージ数, 会話ID
```

### データベース構造検証

```bash
# データベース構造の詳細検証
python -m src.main validate-database
```

**問題がある場合の自動修正:**
```bash
python -m src.main validate-database
# 問題が発見された場合、修正を提案
# "データベース構造を自動修正しますか？" → y
```

## 🚨 トラブルシューティング

### 認証エラー (401 Unauthorized)

**症状:**
```
❌ API接続失敗: 401 Client Error: Unauthorized
```

**解決方法:**
1. Integration Token が正しいか確認
2. Token の前後にスペースがないか確認
3. Token が `secret_` で始まっているか確認
4. Integration が削除されていないか確認

### データベースアクセスエラー (404 Not Found)

**症状:**
```
❌ データベースアクセスエラー: 404 Client Error: Not Found
```

**解決方法:**
1. Database ID が正しいか確認
2. Integration がデータベースに招待されているか確認
3. データベースが削除されていないか確認

### データベース構造エラー

**症状:**
```
❌ データベース構造に問題があります:
  • Missing property: トピック
  • Property 'ステータス' has type 'rich_text', expected 'select'
```

**解決方法:**
```bash
# 自動修正実行
python -m src.main validate-database
# 修正を確認後、"y" を入力
```

### Integration権限不足

**症状:**
```
❌ 権限エラー: Integration does not have access
```

**解決方法:**
1. データベースの「Share」設定を確認
2. Integration の権限が「Can edit」になっているか確認
3. Integration を一度削除してから再度招待

## 🔧 高度な設定

### API制限対応

大量データを扱う場合の設定調整：

```env
# より保守的な設定
NOTION_API_DELAY=0.2
MAX_RETRIES=5
BATCH_SIZE=5

# より積極的な設定（小規模データ用）
NOTION_API_DELAY=0.05
MAX_RETRIES=2
BATCH_SIZE=20
```

### ログ設定

```env
# デバッグログを有効化
LOG_LEVEL=DEBUG
LOG_FILE=logs/debug.log

# エラーのみログ出力
LOG_LEVEL=ERROR
```

### カスタムデータベーススキーマ

既存のデータベースを使用する場合、必要なプロパティ：

| プロパティ名 | 型 | 必須 | 説明 |
|-------------|-----|------|------|
| タイトル | Title | ✅ | ページタイトル |
| 日付 | Date | ✅ | 会話作成日 |
| トピック | Select | ✅ | 自動分類結果 |
| ステータス | Select | ✅ | 処理状態 |
| 要約 | Rich Text | ✅ | 会話要約 |
| 参考になった度 | Select | ✅ | 評価 |
| メッセージ数 | Number | ✅ | メッセージ数 |
| 会話ID | Rich Text | ✅ | ユニークID |

## 🎯 次のステップ

セットアップが完了したら：

1. **サンプルデータでテスト**
   ```bash
   python -m src.main import data/sample_conversations.json --dry-run
   ```

2. **実際のデータインポート**
   ```bash
   python -m src.main import path/to/your/conversations.json
   ```

3. **[使用方法ガイド](usage.md)** を参照してさらなる活用方法を学習

---

セットアップで問題が発生した場合は、エラーメッセージと実行したコマンドを含めてIssueを作成してください。