"""
Main CLI interface for Claude Conversation Importer
"""
import sys
import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

from config.settings import get_settings
from src.utils.logger import setup_logger, get_logger
from src.parsers.conversations_parser import ConversationsParser, validate_json_structure, detect_json_schema
from src.notion.client import NotionConnectionTester, NotionDatabaseManager
from src.notion.database_manager import ConversationImporter

# Setup
console = Console()
setup_logger()
logger = get_logger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(verbose):
    """Claude Conversation Importer - Import Claude conversations to Notion"""
    if verbose:
        logger.info("Verbose mode enabled")


@cli.command()
@click.option('--interactive', '-i', is_flag=True, help='Interactive setup mode')
def setup(interactive):
    """Setup Notion integration and configuration"""
    console.print(Panel.fit("🔧 Claude Conversation Importer - 初期設定", style="bold blue"))
    
    if interactive:
        _interactive_setup()
    else:
        _check_current_setup()


def _interactive_setup():
    """Interactive setup process"""
    console.print("Notion Integration Token を入力してください:")
    console.print("(https://www.notion.so/my-integrations で取得)")
    
    token = click.prompt("Token", hide_input=True)
    
    # Test connection
    console.print("🔗 Notion API接続をテストしています...")
    tester = NotionConnectionTester(token)
    results = tester.test_connection()
    
    if not results["api_connection"]:
        console.print(f"❌ API接続失敗: {results['error_message']}", style="bold red")
        return
    
    console.print("✅ Notion API接続成功", style="bold green")
    
    # List databases
    databases = tester.list_accessible_databases()
    
    if databases:
        console.print("\nアクセス可能なデータベース:")
        table = Table()
        table.add_column("番号", style="cyan")
        table.add_column("タイトル", style="magenta")
        table.add_column("ID", style="dim")
        
        for i, db in enumerate(databases, 1):
            table.add_row(str(i), db["title"], db["id"])
        
        console.print(table)
        console.print("0. 新規データベースを作成")
        
        choice = click.prompt("使用するデータベース番号", type=int)
        
        if choice == 0:
            # Create new database
            parent_page_id = click.prompt("親ページID（新規データベース作成用）")
            db_title = click.prompt("データベース名", default="Claude会話ログ")
            
            try:
                manager = NotionDatabaseManager(token)
                db_id = manager.create_database(parent_page_id, db_title)
                console.print(f"✅ データベース作成成功: {db_id}", style="bold green")
            except Exception as e:
                console.print(f"❌ データベース作成失敗: {e}", style="bold red")
                return
        else:
            if 1 <= choice <= len(databases):
                db_id = databases[choice - 1]["id"]
                console.print(f"選択されたデータベース: {databases[choice - 1]['title']}")
            else:
                console.print("無効な選択です", style="bold red")
                return
    else:
        parent_page_id = click.prompt("親ページID（新規データベース作成用）")
        try:
            manager = NotionDatabaseManager(token)
            db_id = manager.create_database(parent_page_id)
            console.print(f"✅ データベース作成成功: {db_id}", style="bold green")
        except Exception as e:
            console.print(f"❌ データベース作成失敗: {e}", style="bold red")
            return
    
    # Generate .env file
    env_content = f"""NOTION_TOKEN={token}
NOTION_DATABASE_ID={db_id}
LOG_LEVEL=INFO
BATCH_SIZE=10
IMPORT_MODE=update
AUTO_CREATE_DATABASE=false
NOTION_API_DELAY=0.1
MAX_RETRIES=3
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    console.print("✅ 設定完了！.env ファイルが作成されました", style="bold green")


def _check_current_setup():
    """Check current configuration"""
    try:
        settings = get_settings()
        console.print("現在の設定:")
        
        table = Table()
        table.add_column("設定項目", style="cyan")
        table.add_column("値", style="magenta")
        
        table.add_row("Database ID", settings.notion_database_id or "未設定")
        table.add_row("Log Level", settings.log_level)
        table.add_row("Batch Size", str(settings.batch_size))
        table.add_row("Import Mode", settings.import_mode)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"❌ 設定読み込みエラー: {e}", style="bold red")


@cli.command()
def test_connection():
    """Test Notion API connection"""
    try:
        settings = get_settings()
        
        console.print("🔗 Notion API接続をテストしています...")
        
        tester = NotionConnectionTester(settings.notion_token, settings.notion_database_id)
        results = tester.test_connection()
        
        # Display results
        table = Table(title="接続テスト結果")
        table.add_column("項目", style="cyan")
        table.add_column("結果", style="magenta")
        table.add_column("詳細", style="dim")
        
        api_status = "✅ 成功" if results["api_connection"] else "❌ 失敗"
        table.add_row("API接続", api_status, "")
        
        if settings.notion_database_id:
            db_status = "✅ 成功" if results["database_access"] else "❌ 失敗"
            table.add_row("データベースアクセス", db_status, "")
            
            structure_status = "✅ 適合" if results["database_structure"] else "❌ 不適合"
            table.add_row("データベース構造", structure_status, results.get("error_message", ""))
        
        console.print(table)
        
        if results["database_info"]:
            console.print(f"\nデータベース情報:")
            console.print(f"タイトル: {results['database_info']['title']}")
            console.print(f"プロパティ: {', '.join(results['database_info']['properties'])}")
        
    except Exception as e:
        console.print(f"❌ テスト失敗: {e}", style="bold red")


@cli.command()
@click.argument('database_id', required=False)
def validate_database(database_id):
    """Validate database structure"""
    try:
        settings = get_settings()
        db_id = database_id or settings.notion_database_id
        
        if not db_id:
            console.print("❌ データベースIDが指定されていません", style="bold red")
            return
        
        console.print(f"📊 データベース構造を検証しています: {db_id}")
        
        manager = NotionDatabaseManager(settings.notion_token, db_id)
        is_valid, issues = manager.validate_database_structure(db_id)
        
        if is_valid:
            console.print("✅ データベース構造は正常です", style="bold green")
        else:
            console.print("❌ データベース構造に問題があります:", style="bold red")
            for issue in issues:
                console.print(f"  • {issue}")
            
            if click.confirm("データベース構造を自動修正しますか？"):
                success = manager.update_database_properties(db_id)
                if success:
                    console.print("✅ データベース構造を修正しました", style="bold green")
                else:
                    console.print("❌ 修正に失敗しました", style="bold red")
    
    except Exception as e:
        console.print(f"❌ 検証エラー: {e}", style="bold red")


@cli.command()
@click.argument('json_file', type=click.Path(exists=True))
def stats(json_file):
    """Show statistics about conversations.json file"""
    try:
        console.print(f"📊 ファイル統計を分析しています: {json_file}")
        
        parser = ConversationsParser(json_file)
        file_stats = parser.get_file_stats()
        
        # File info
        console.print(Panel.fit(f"ファイル: {json_file}\nサイズ: {file_stats['file_size_mb']:.2f} MB", title="ファイル情報"))
        
        # Statistics table
        table = Table(title="会話統計")
        table.add_column("項目", style="cyan")
        table.add_column("値", style="magenta")
        
        table.add_row("総会話数", str(file_stats['total_conversations']))
        table.add_row("総メッセージ数", str(file_stats['total_messages']))
        table.add_row("平均メッセージ/会話", f"{file_stats['average_messages_per_conversation']:.1f}")
        
        if file_stats['date_range']['earliest']:
            table.add_row("最初の会話", file_stats['date_range']['earliest'].strftime('%Y-%m-%d'))
        if file_stats['date_range']['latest']:
            table.add_row("最新の会話", file_stats['date_range']['latest'].strftime('%Y-%m-%d'))
        
        console.print(table)
        
        # Topic distribution
        if file_stats['topic_distribution']:
            topic_table = Table(title="トピック分布")
            topic_table.add_column("トピック", style="cyan")
            topic_table.add_column("会話数", style="magenta")
            
            for topic, count in sorted(file_stats['topic_distribution'].items(), key=lambda x: x[1], reverse=True):
                topic_table.add_row(topic, str(count))
            
            console.print(topic_table)
    
    except Exception as e:
        console.print(f"❌ 統計分析エラー: {e}", style="bold red")


@cli.command()
@click.argument('json_file', type=click.Path(exists=True))
@click.option('--batch-size', '-b', type=int, help='Batch size for import')
@click.option('--mode', '-m', type=click.Choice(['update', 'create_only', 'overwrite']), help='Import mode')
@click.option('--dry-run', '-d', is_flag=True, help='Test run without actual import')
@click.option('--topic-analysis', '-t', is_flag=True, help='Enable automatic topic analysis')
@click.option('--filter-date', nargs=2, help='Filter by date range (start_date end_date)')
def import_conversations(json_file, batch_size, mode, dry_run, topic_analysis, filter_date):
    """Import conversations from JSON file to Notion"""
    try:
        settings = get_settings()
        
        # Override settings with command line options
        if batch_size:
            settings.batch_size = batch_size
        if mode:
            settings.import_mode = mode
        
        console.print(Panel.fit(f"📥 会話インポート開始\nファイル: {json_file}\nモード: {settings.import_mode}", title="インポート設定"))
        
        if dry_run:
            console.print("🧪 ドライランモード - 実際のインポートは行いません", style="bold yellow")
        
        # Validate JSON file
        console.print("📋 JSONファイルを検証しています...")
        is_valid, errors = validate_json_structure(json_file)
        if not is_valid:
            console.print("❌ JSONファイルに問題があります:", style="bold red")
            for error in errors:
                console.print(f"  • {error}")
            return
        
        # Parse conversations
        console.print("🔍 会話を解析しています...")
        parser = ConversationsParser(json_file)
        conversations = parser.parse()
        
        if not conversations:
            console.print("❌ 有効な会話が見つかりませんでした", style="bold red")
            return
        
        console.print(f"✅ {len(conversations)}件の会話を解析しました", style="bold green")
        
        # Filter by date if specified
        if filter_date:
            start_date, end_date = filter_date
            # TODO: Implement date filtering
            console.print(f"📅 日付フィルター: {start_date} - {end_date}")
        
        if not dry_run:
            # Test Notion connection
            console.print("🔗 Notion接続をテストしています...")
            tester = NotionConnectionTester(settings.notion_token, settings.notion_database_id)
            results = tester.test_connection()
            
            if not results["database_access"]:
                console.print(f"❌ データベースアクセスエラー: {results['error_message']}", style="bold red")
                return
        
        # Import conversations
        console.print("🚀 インポートを開始します...")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Importing conversations...", total=len(conversations))
            
            if not dry_run:
                importer = ConversationImporter(settings.notion_token, settings.notion_database_id)
                stats_result = importer.batch_import(
                    conversations, 
                    batch_size=settings.batch_size,
                    mode=settings.import_mode,
                    dry_run=dry_run
                )
            else:
                # Simulate import for dry run
                stats_result = {
                    "total": len(conversations),
                    "created": len(conversations),
                    "updated": 0,
                    "skipped": 0,
                    "errors": 0
                }
            
            progress.update(task, completed=len(conversations))
        
        # Show results
        result_table = Table(title="インポート結果")
        result_table.add_column("項目", style="cyan")
        result_table.add_column("件数", style="magenta")
        
        result_table.add_row("総数", str(stats_result["total"]))
        result_table.add_row("作成", str(stats_result["created"]))
        result_table.add_row("更新", str(stats_result["updated"]))
        result_table.add_row("スキップ", str(stats_result["skipped"]))
        result_table.add_row("エラー", str(stats_result["errors"]))
        
        console.print(result_table)
        
        if stats_result["errors"] == 0:
            console.print("✅ インポート完了！", style="bold green")
        else:
            console.print(f"⚠️  インポート完了（{stats_result['errors']}件のエラーあり）", style="bold yellow")
    
    except Exception as e:
        console.print(f"❌ インポートエラー: {e}", style="bold red")
        logger.exception("Import failed")


@cli.command()
def config():
    """Show current configuration"""
    _check_current_setup()


@cli.command()
def list_databases():
    """List accessible Notion databases"""
    try:
        settings = get_settings()
        
        console.print("📊 アクセス可能なデータベースを取得しています...")
        
        tester = NotionConnectionTester(settings.notion_token)
        databases = tester.list_accessible_databases()
        
        if databases:
            table = Table(title="アクセス可能なデータベース")
            table.add_column("タイトル", style="cyan")
            table.add_column("ID", style="magenta")
            table.add_column("URL", style="dim")
            
            for db in databases:
                table.add_row(db["title"], db["id"], db["url"])
            
            console.print(table)
        else:
            console.print("アクセス可能なデータベースが見つかりませんでした")
    
    except Exception as e:
        console.print(f"❌ データベース取得エラー: {e}", style="bold red")


if __name__ == '__main__':
    cli()