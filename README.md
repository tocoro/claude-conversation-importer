# Claude Conversation Importer

Claude.ai公式のデータエクスポート機能から取得した`conversations.json`ファイルを解析し、Notionデータベースに自動インポートするPythonツールです。

## 🎯 概要

このツールは以下の機能を提供します：

- **conversations.jsonの解析**: Claude.aiから出力された会話履歴の自動解析
- **Notion自動インポート**: 構造化されたデータベースへの一括インポート
- **自動分類**: 会話内容に基づくトピック自動分類
- **多言語翻訳**: OpenAI GPTとGoogle Geminiを使った日本語タイトル翻訳
- **重複管理**: 既存データの更新・スキップ・上書きオプション
- **エラーハンドリング**: 堅牢なエラー処理とリトライ機能

## 📋 必要環境

- Python 3.8以上
- Notion API Integration Token
- Notionワークスペースのアクセス権限

## 🚀 インストール

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd claude-notion-importer
```

### 2. 仮想環境の作成（推奨）

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
```

### 3. 依存関係のインストール

```bash
pip install -r requirements.txt
```

## ⚙️ セットアップ

### 1. Notion Integrationの作成

1. [Notion Integrations](https://www.notion.so/my-integrations) にアクセス
2. 「New integration」をクリック
3. Integration情報を入力：
   - Name: `Claude Conversation Importer`
   - Capabilities: `Read content`, `Update content`, `Insert content`
4. 作成後、Integration Tokenをコピー

### 2. データベースの準備

#### 既存データベースを使用する場合

1. Notionで「Claude会話ログ」データベースを開く
2. 右上の「Share」→ 作成したIntegrationを招待
3. URLからDatabase IDを取得

#### 新規データベースを作成する場合

ツールが自動作成します（後述の対話式セットアップを使用）

### 3. 環境変数の設定

#### 対話式セットアップ（推奨）

```bash
python -m src.main setup --interactive
```

#### 手動セットアップ

`.env.example`を`.env`にコピーして編集：

```bash
cp .env.example .env
```

```env
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 翻訳機能を使用する場合（オプション）
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

## 🔧 使用方法

### 基本的な使用法

```bash
# 接続テスト
python -m src.main test-connection

# ファイル統計の確認
python -m src.main stats data/conversations.json

# 基本インポート
python -m src.main import-conversations data/conversations.json

# ドライラン（テスト実行）
python -m src.main import-conversations data/conversations.json --dry-run
```

### 高度なオプション

```bash
# バッチサイズとモードを指定
python -m src.main import-conversations data/conversations.json \
  --batch-size 5 \
  --mode update \
  --topic-analysis

# 日付範囲でフィルター
python -m src.main import-conversations data/conversations.json \
  --filter-date 2024-01-01 2024-12-31
```

### インポートモード

- `update`: 既存データを更新、新規データを作成（デフォルト）
- `create_only`: 新規データのみ作成、既存データはスキップ
- `overwrite`: 既存データを削除して再作成

## 📊 データベーススキーマ

作成されるNotionデータベースには以下のプロパティが含まれます：

| プロパティ名 | 型 | 説明 |
|-------------|-----|------|
| タイトル | Title | 会話のタイトル |
| 邦訳タイトル | Rich Text | AI翻訳された日本語タイトル |
| 日付 | Date | 会話作成日 |
| トピック | Select | 自動分類されたトピック |
| ステータス | Select | 会話の状態 |
| 要約 | Rich Text | 会話の要約 |
| 参考になった度 | Select | 評価（⭐1-5） |
| メッセージ数 | Number | 会話内のメッセージ数 |
| 会話ID | Rich Text | ユニークID |
| Claude会話URL | URL | Claude.aiの会話へのリンク |

### トピック分類

- **技術相談**: プログラミング、API、エラー、デバッグ関連
- **作業効率化**: 自動化、ワークフロー、効率化関連
- **学習・調査**: 調査、説明、学習関連
- **創作・アイデア**: アイデア、創作、企画関連
- **日常会話**: 挨拶、雑談関連
- **その他**: 上記に該当しない内容

## 🛠️ CLI コマンド一覧

### セットアップ・設定

```bash
# 対話式セットアップ
python -m src.main setup --interactive

# 現在の設定表示
python -m src.main config

# 接続テスト
python -m src.main test-connection

# データベース構造検証
python -m src.main validate-database

# アクセス可能なデータベース一覧
python -m src.main list-databases
```

### データ分析・インポート

```bash
# ファイル統計表示
python -m src.main stats <json_file>

# 基本インポート
python -m src.main import-conversations <json_file>

# オプション付きインポート
python -m src.main import-conversations <json_file> \
  --batch-size <N> \
  --mode <update|create_only|overwrite> \
  --dry-run \
  --topic-analysis \
  --filter-date <start> <end>
```

## 🔍 トラブルシューティング

### よくある問題

#### 1. 認証エラー (401 Unauthorized)
- Integration Tokenが正しく設定されているか確認
- `.env`ファイルの`NOTION_TOKEN`を再確認

#### 2. データベースアクセスエラー (404 Not Found)
- Database IDが正しいか確認
- Integrationがデータベースにアクセス権を持っているか確認

#### 3. プロパティエラー
```bash
# データベース構造を自動修正
python -m src.main validate-database --fix
```

#### 4. JSON解析エラー
- conversations.jsonファイルの形式を確認
- ファイルが破損していないか確認

### ログの確認

```bash
# ログファイルの場所
tail -f logs/importer.log

# 詳細ログで実行
python -m src.main import-conversations <json_file> --verbose
```

## 🧪 テスト

```bash
# 全テスト実行
pytest

# 特定のテストファイル
pytest tests/test_parser.py

# カバレッジ付きテスト
pytest --cov=src tests/
```

## 📈 パフォーマンス

### 推奨設定

- **バッチサイズ**: 10-20件（Notion API制限を考慮）
- **API遅延**: 0.1秒（レート制限対応）
- **最大リトライ**: 3回

### 大量データの処理

```bash
# 大量データの場合はバッチサイズを調整
python -m src.main import-conversations large_conversations.json \
  --batch-size 5 \
  --mode create_only
```

## 🔒 セキュリティ

- API Tokenは`.env`ファイルで管理（Gitにコミットしない）
- `.gitignore`で機密情報を除外
- 最小限の権限でIntegrationを作成

## 🤝 コントリビューション

1. Forkしてブランチを作成
2. 変更を実装
3. テストを追加・実行
4. Pull Requestを作成

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🆘 サポート

問題が発生した場合は、以下の情報と共にIssueを作成してください：

- エラーメッセージ
- 実行したコマンド
- conversations.jsonの構造例
- 環境情報（Python版、OS等）

---

**注意**: このツールはClaude.ai公式のデータエクスポート機能を前提としています。データ形式が変更された場合、アップデートが必要になる可能性があります。