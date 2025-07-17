"""
Configuration settings for Claude Conversation Importer
"""
import os
from typing import Dict, List, Optional
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # Notion API settings
    notion_token: str = Field(..., env="NOTION_TOKEN")
    notion_database_id: Optional[str] = Field(None, env="NOTION_DATABASE_ID")
    notion_parent_page_id: Optional[str] = Field(None, env="NOTION_PARENT_PAGE_ID")
    
    # Application settings
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("logs/importer.log", env="LOG_FILE")
    batch_size: int = Field(10, env="BATCH_SIZE")
    import_mode: str = Field("update", env="IMPORT_MODE")
    auto_create_database: bool = Field(False, env="AUTO_CREATE_DATABASE")
    
    # API settings
    notion_api_delay: float = Field(0.1, env="NOTION_API_DELAY")
    max_retries: int = Field(3, env="MAX_RETRIES")
    
    # Translation API settings
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Notion database schema constants
REQUIRED_PROPERTIES = {
    "タイトル": "title",
    "邦訳タイトル": "rich_text",
    "日付": "date", 
    "トピック": "select",
    "ステータス": "select",
    "要約": "rich_text",
    "参考になった度": "select",
    "メッセージ数": "number",
    "会話ID": "rich_text",
    "Claude会話URL": "url"
}

SELECT_OPTIONS = {
    "トピック": ["技術相談", "作業効率化", "学習・調査", "創作・アイデア", "日常会話", "その他"],
    "ステータス": ["進行中", "完了", "要フォローアップ"],
    "参考になった度": ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]
}

DATABASE_SCHEMA = {
    "title": [{"text": {"content": "Claude会話ログ"}}],
    "properties": {
        "タイトル": {"title": {}},
        "邦訳タイトル": {"rich_text": {}},
        "日付": {"date": {}},
        "トピック": {
            "select": {
                "options": [
                    {"name": "技術相談", "color": "blue"},
                    {"name": "作業効率化", "color": "green"},
                    {"name": "学習・調査", "color": "orange"},
                    {"name": "創作・アイデア", "color": "purple"},
                    {"name": "日常会話", "color": "gray"},
                    {"name": "その他", "color": "default"}
                ]
            }
        },
        "ステータス": {
            "select": {
                "options": [
                    {"name": "進行中", "color": "yellow"},
                    {"name": "完了", "color": "green"},
                    {"name": "要フォローアップ", "color": "red"}
                ]
            }
        },
        "要約": {"rich_text": {}},
        "参考になった度": {
            "select": {
                "options": [
                    {"name": "⭐", "color": "red"},
                    {"name": "⭐⭐", "color": "orange"},
                    {"name": "⭐⭐⭐", "color": "yellow"},
                    {"name": "⭐⭐⭐⭐", "color": "blue"},
                    {"name": "⭐⭐⭐⭐⭐", "color": "green"}
                ]
            }
        },
        "メッセージ数": {"number": {}},
        "会話ID": {"rich_text": {}},
        "Claude会話URL": {"url": {}}
    }
}

# Topic classification keywords
TOPIC_KEYWORDS = {
    "技術相談": ["プログラミング", "API", "エラー", "デバッグ", "コード", "開発", "実装", "バグ"],
    "作業効率化": ["自動化", "ワークフロー", "効率", "時間短縮", "最適化", "改善"],
    "学習・調査": ["調べて", "教えて", "説明", "学習", "理解", "勉強", "研究"],
    "創作・アイデア": ["アイデア", "創作", "ブレインストーミング", "企画", "デザイン", "作成"],
    "日常会話": ["こんにちは", "ありがとう", "雑談", "挨拶", "お疲れ"]
}

def get_settings() -> Settings:
    """Get application settings"""
    return Settings()

def ensure_log_directory():
    """Ensure log directory exists"""
    settings = get_settings()
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)