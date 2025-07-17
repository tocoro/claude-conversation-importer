# 使用方法ガイド

Claude Conversation Importerの詳細な使用方法を説明します。

## 🚀 基本的な使用の流れ

### 1. データの準備と確認

```bash
# conversations.jsonファイルの統計情報を確認
python -m src.main stats data/conversations.json
```

**出力例:**
```
📊 ファイル統計を分析しています: data/conversations.json

┌─ ファイル情報 ─────────────────────────────┐
│ ファイル: data/conversations.json        │
│ サイズ: 2.45 MB                          │
└─────────────────────────────────────────────┘

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 項目                       ┃ 値                         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 総会話数                   │ 150                        │
│ 総メッセージ数             │ 1,247                      │
│ 平均メッセージ/会話        │ 8.3                        │
│ 最初の会話                 │ 2024-01-15                 │
│ 最新の会話                 │ 2024-07-16                 │
└────────────────────────────┴────────────────────────────┘

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ トピック                   ┃ 会話数                     ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 技術相談                   │ 45                         │
│ 学習・調査                 │ 38                         │
│ 作業効率化                 │ 32                         │
│ 創作・アイデア             │ 20                         │
│ 日常会話                   │ 10                         │
│ その他                     │ 5                          │
└────────────────────────────┴────────────────────────────┘
```

### 2. ドライラン（テスト実行）

```bash
# 実際のインポートを行わずにテスト
python -m src.main import data/conversations.json --dry-run
```

### 3. 実際のインポート

```bash
# 基本インポート
python -m src.main import data/conversations.json
```

## 📊 コマンドラインオプション詳細

### import コマンド

```bash
python -m src.main import <json_file> [OPTIONS]
```

#### 主要オプション

| オプション | 短縮形 | 説明 | デフォルト |
|-----------|--------|------|------------|
| `--batch-size` | `-b` | バッチサイズ | 10 |
| `--mode` | `-m` | インポートモード | update |
| `--dry-run` | `-d` | テスト実行 | False |
| `--topic-analysis` | `-t` | トピック分析有効化 | False |
| `--filter-date` | なし | 日付範囲フィルター | なし |
| `--verbose` | `-v` | 詳細ログ | False |

#### インポートモード詳細

##### `update` モード（推奨）
```bash
python -m src.main import data/conversations.json --mode update
```
- **新規会話**: 新しいページを作成
- **既存会話**: 内容を更新（差分があれば）
- **用途**: 継続的なインポート、定期実行

##### `create_only` モード
```bash
python -m src.main import data/conversations.json --mode create_only
```
- **新規会話**: 新しいページを作成
- **既存会話**: スキップ（変更なし）
- **用途**: 初回インポート、重複を避けたい場合

##### `overwrite` モード
```bash
python -m src.main import data/conversations.json --mode overwrite
```
- **新規会話**: 新しいページを作成
- **既存会話**: 完全に置き換え
- **用途**: データの完全リセット、構造変更後

### バッチサイズの調整

```bash
# 小さなバッチサイズ（安全、遅い）
python -m src.main import data/conversations.json --batch-size 5

# 大きなバッチサイズ（高速、リスク高）
python -m src.main import data/conversations.json --batch-size 20

# 推奨設定（バランス良）
python -m src.main import data/conversations.json --batch-size 10
```

**バッチサイズ選択の指針:**
- **5件以下**: 大量データ、Notion API制限回避
- **10-15件**: 標準的な使用（推奨）
- **20件以上**: 小規模データ、高速処理

### 日付フィルター

```bash
# 特定期間のみインポート
python -m src.main import data/conversations.json \
  --filter-date 2024-01-01 2024-06-30

# 最近の会話のみ
python -m src.main import data/conversations.json \
  --filter-date 2024-07-01 2024-07-16
```

## 🔍 高度な使用法

### 1. 段階的インポート

大量データを安全にインポートする方法：

```bash
# Step 1: ドライランで確認
python -m src.main import large_conversations.json --dry-run

# Step 2: 小さなバッチで開始
python -m src.main import large_conversations.json \
  --batch-size 5 \
  --mode create_only

# Step 3: 確認後に残りを処理
python -m src.main import large_conversations.json \
  --mode update
```

### 2. エラー時の対処

```bash
# 詳細ログで問題を特定
python -m src.main import data/conversations.json \
  --verbose \
  --batch-size 1

# ログファイルを確認
tail -f logs/importer.log
```

### 3. 継続的な更新

定期的に新しい会話をインポートする場合：

```bash
# 新しいデータのみ追加
python -m src.main import new_conversations.json \
  --mode create_only

# 全データを最新状態に更新
python -m src.main import all_conversations.json \
  --mode update
```

## 📈 パフォーマンス最適化

### Notion API制限について

Notion APIには以下の制限があります：
- **レート制限**: 3リクエスト/秒
- **ページサイズ制限**: 100項目/リクエスト
- **コンテンツサイズ制限**: 2000文字/ブロック

### 最適化設定

#### 高速処理（小規模データ用）
```bash
# .envファイルで設定
NOTION_API_DELAY=0.05
BATCH_SIZE=15
MAX_RETRIES=2

# または一時的に指定
python -m src.main import data/conversations.json \
  --batch-size 15
```

#### 安全処理（大規模データ用）
```bash
# .envファイルで設定
NOTION_API_DELAY=0.2
BATCH_SIZE=5
MAX_RETRIES=5

# または一時的に指定
python -m src.main import data/conversations.json \
  --batch-size 5
```

### 処理時間の目安

| 会話数 | バッチサイズ | 予想時間 | 推奨設定 |
|--------|--------------|----------|----------|
| 50件 | 10 | 2-3分 | 標準 |
| 200件 | 10 | 8-12分 | 標準 |
| 500件 | 5 | 25-35分 | 安全 |
| 1000件+ | 5 | 50分+ | 安全 + 分割実行 |

## 🛠️ カスタマイズ

### 1. トピック分類のカスタマイズ

`config/settings.py`でキーワードを編集：

```python
TOPIC_KEYWORDS = {
    "技術相談": ["プログラミング", "API", "エラー", "デバッグ", "コード", "開発"],
    "作業効率化": ["自動化", "ワークフロー", "効率", "時間短縮", "最適化"],
    "学習・調査": ["調べて", "教えて", "説明", "学習", "理解", "勉強"],
    "創作・アイデア": ["アイデア", "創作", "ブレインストーミング", "企画"],
    "日常会話": ["こんにちは", "ありがとう", "雑談", "挨拶"],
    # カスタムトピックを追加
    "ビジネス": ["売上", "営業", "マーケティング", "戦略"],
    "研究": ["論文", "実験", "仮説", "分析", "データ"]
}
```

### 2. データベーススキーマの拡張

新しいプロパティを追加する場合：

1. Notionデータベースに手動でプロパティを追加
2. `config/settings.py`の`REQUIRED_PROPERTIES`を更新
3. インポートロジックを修正

### 3. ログ設定のカスタマイズ

```bash
# 環境変数で設定
export LOG_LEVEL=DEBUG
export LOG_FILE=logs/custom.log

# または.envファイルで設定
LOG_LEVEL=DEBUG
LOG_FILE=logs/custom.log
```

## 🚨 エラーハンドリング

### 一般的なエラーと対処法

#### 1. JSONファイルエラー
```
❌ JSONファイルに問題があります:
  • Invalid JSON: Expecting ',' delimiter
```

**対処法:**
- ファイルが正しいJSONフォーマットか確認
- テキストエディタでファイルを開いて構文チェック
- サンプルファイルと比較

#### 2. API制限エラー
```
❌ API Error: 429 Too Many Requests
```

**対処法:**
```bash
# バッチサイズを小さくして実行
python -m src.main import data/conversations.json --batch-size 3

# またはAPI遅延を増やす（.envファイル）
NOTION_API_DELAY=0.3
```

#### 3. メモリエラー
```
❌ MemoryError: unable to allocate array
```

**対処法:**
- 大きなJSONファイルを分割
- バッチサイズを小さくする
- 不要なメッセージを事前にフィルター

### リカバリー手順

#### 部分失敗からの復旧
```bash
# 1. エラーログを確認
tail -100 logs/importer.log

# 2. 失敗した会話を特定
python -m src.main import data/conversations.json \
  --mode create_only \
  --verbose

# 3. 成功した分はスキップして続行
python -m src.main import data/conversations.json \
  --mode update
```

## 📊 結果の分析

### インポート結果の確認

```bash
# Notionデータベースの統計（手動確認）
# - 総ページ数
# - トピック別分布
# - 日付範囲
# - エラーがあったページ
```

### データ品質チェック

1. **重複チェック**: 同じ会話IDが複数ないか
2. **データ整合性**: メッセージ数が正しいか
3. **分類精度**: トピック分類が適切か
4. **日付範囲**: 期待される期間のデータがあるか

## 🔄 定期実行の設定

### cronでの自動実行

```bash
# crontabを編集
crontab -e

# 毎日午前2時に新しい会話をインポート
0 2 * * * cd /path/to/claude-notion-importer && python -m src.main import /path/to/new_conversations.json --mode create_only

# 毎週日曜日に全データを更新
0 3 * * 0 cd /path/to/claude-notion-importer && python -m src.main import /path/to/all_conversations.json --mode update
```

### バッチスクリプト例

```bash
#!/bin/bash
# import_daily.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 仮想環境をアクティベート
source venv/bin/activate

# 新しい会話をダウンロード（要実装）
# download_new_conversations.py

# インポート実行
python -m src.main import data/new_conversations.json \
  --mode create_only \
  --batch-size 10

# ログローテーション
find logs/ -name "*.log" -mtime +30 -delete

echo "Daily import completed: $(date)"
```

---

このガイドを参考に、あなたの用途に最適な設定でClaude Conversation Importerを活用してください。追加の質問やカスタマイズが必要な場合は、Issueを作成してお知らせください。