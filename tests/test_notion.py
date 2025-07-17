"""
Tests for Notion integration modules
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.notion.client import NotionConnectionTester, NotionDatabaseManager
from src.notion.database_manager import ConversationImporter
from src.parsers.conversations_parser import ParsedConversation, ParsedMessage


class TestNotionConnectionTester:
    """Test cases for NotionConnectionTester"""
    
    @patch('src.notion.client.Client')
    def test_successful_connection(self, mock_client_class):
        """Test successful API connection"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.users.me.return_value = {"id": "user_123"}
        
        tester = NotionConnectionTester("test_token")
        results = tester.test_connection()
        
        assert results["api_connection"] is True
        assert results["error_message"] is None
        mock_client.users.me.assert_called_once()
    
    @patch('src.notion.client.Client')
    def test_database_access_success(self, mock_client_class):
        """Test successful database access"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.users.me.return_value = {"id": "user_123"}
        mock_client.databases.retrieve.return_value = {
            "title": [{"text": {"content": "Test Database"}}],
            "properties": {
                "タイトル": {"type": "title"},
                "日付": {"type": "date"},
                "トピック": {"type": "select"}
            }
        }
        
        tester = NotionConnectionTester("test_token", "db_123")
        results = tester.test_connection()
        
        assert results["api_connection"] is True
        assert results["database_access"] is True
        assert results["database_info"]["title"] == "Test Database"
        assert "タイトル" in results["database_info"]["properties"]
    
    @patch('src.notion.client.Client')
    def test_api_connection_failure(self, mock_client_class):
        """Test API connection failure"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.users.me.side_effect = Exception("Authentication failed")
        
        tester = NotionConnectionTester("invalid_token")
        results = tester.test_connection()
        
        assert results["api_connection"] is False
        assert "Authentication failed" in results["error_message"]
    
    @patch('src.notion.client.Client')
    def test_list_accessible_databases(self, mock_client_class):
        """Test listing accessible databases"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.search.return_value = {
            "results": [
                {
                    "id": "db_001",
                    "title": [{"text": {"content": "Database 1"}}],
                    "url": "https://notion.so/db1"
                },
                {
                    "id": "db_002", 
                    "title": [{"text": {"content": "Database 2"}}],
                    "url": "https://notion.so/db2"
                }
            ]
        }
        
        tester = NotionConnectionTester("test_token")
        databases = tester.list_accessible_databases()
        
        assert len(databases) == 2
        assert databases[0]["id"] == "db_001"
        assert databases[0]["title"] == "Database 1"
        assert databases[1]["id"] == "db_002"


class TestNotionDatabaseManager:
    """Test cases for NotionDatabaseManager"""
    
    @patch('src.notion.client.Client')
    def test_create_database_success(self, mock_client_class):
        """Test successful database creation"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.databases.create.return_value = {"id": "new_db_123"}
        
        manager = NotionDatabaseManager("test_token")
        db_id = manager.create_database("parent_page_123", "Test Database")
        
        assert db_id == "new_db_123"
        mock_client.databases.create.assert_called_once()
    
    @patch('src.notion.client.Client')
    def test_validate_database_structure_valid(self, mock_client_class):
        """Test validation of valid database structure"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.databases.retrieve.return_value = {
            "properties": {
                "タイトル": {"type": "title"},
                "邦訳タイトル": {"type": "rich_text"},
                "日付": {"type": "date"},
                "トピック": {"type": "select", "select": {"options": [
                    {"name": "技術相談"}, {"name": "作業効率化"}, {"name": "学習・調査"}, 
                    {"name": "創作・アイデア"}, {"name": "日常会話"}, {"name": "その他"}
                ]}},
                "ステータス": {"type": "select", "select": {"options": [
                    {"name": "進行中"}, {"name": "完了"}, {"name": "要フォローアップ"}
                ]}},
                "要約": {"type": "rich_text"},
                "参考になった度": {"type": "select", "select": {"options": [
                    {"name": "⭐"}, {"name": "⭐⭐"}, {"name": "⭐⭐⭐"}, 
                    {"name": "⭐⭐⭐⭐"}, {"name": "⭐⭐⭐⭐⭐"}
                ]}},
                "メッセージ数": {"type": "number"},
                "会話ID": {"type": "rich_text"},
                "Claude会話URL": {"type": "url"}
            }
        }
        
        manager = NotionDatabaseManager("test_token")
        is_valid, issues = manager.validate_database_structure("db_123")
        
        assert is_valid is True
        assert len(issues) == 0
    
    @patch('src.notion.client.Client')
    def test_validate_database_structure_invalid(self, mock_client_class):
        """Test validation of invalid database structure"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.databases.retrieve.return_value = {
            "properties": {
                "タイトル": {"type": "title"},
                "日付": {"type": "date"}
                # Missing required properties
            }
        }
        
        manager = NotionDatabaseManager("test_token")
        is_valid, issues = manager.validate_database_structure("db_123")
        
        assert is_valid is False
        assert len(issues) > 0
        assert any("Missing property" in issue for issue in issues)
    
    @patch('src.notion.client.Client')
    def test_check_existing_conversation(self, mock_client_class):
        """Test checking for existing conversation"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.databases.query.return_value = {
            "results": [{"id": "existing_page_123"}]
        }
        
        manager = NotionDatabaseManager("test_token", "db_123")
        page_id = manager.check_existing_conversation("conv_123")
        
        assert page_id == "existing_page_123"
        mock_client.databases.query.assert_called_once()


class TestConversationImporter:
    """Test cases for ConversationImporter"""
    
    def create_sample_conversation(self) -> ParsedConversation:
        """Create a sample conversation for testing"""
        messages = [
            ParsedMessage(
                role="human",
                content="Test human message",
                timestamp=datetime(2024, 1, 15, 10, 30)
            ),
            ParsedMessage(
                role="assistant", 
                content="Test assistant response",
                timestamp=datetime(2024, 1, 15, 10, 31)
            )
        ]
        
        return ParsedConversation(
            conversation_id="test_conv_123",
            title="Test Conversation",
            created_at=datetime(2024, 1, 15, 10, 30),
            updated_at=datetime(2024, 1, 15, 10, 35),
            messages=messages,
            message_count=2,
            summary="Test conversation summary",
            topic="技術相談",
            status="完了",
            rating="⭐⭐⭐"
        )
    
    @patch('src.notion.database_manager.Client')
    def test_import_new_conversation(self, mock_client_class):
        """Test importing a new conversation"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock no existing conversation
        mock_client.databases.query.return_value = {"results": []}
        
        # Mock successful page creation
        mock_client.pages.create.return_value = {"id": "new_page_123"}
        
        importer = ConversationImporter("test_token", "db_123")
        conversation = self.create_sample_conversation()
        
        stats = importer.import_conversations([conversation], mode="update")
        
        assert stats["created"] == 1
        assert stats["errors"] == 0
        mock_client.pages.create.assert_called_once()
    
    @patch('src.notion.database_manager.Client')
    def test_import_existing_conversation_update_mode(self, mock_client_class):
        """Test updating an existing conversation in update mode"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock existing conversation found
        mock_client.databases.query.return_value = {
            "results": [{"id": "existing_page_123"}]
        }
        
        # Mock successful page update
        mock_client.pages.update.return_value = {"id": "existing_page_123"}
        mock_client.blocks.children.list.return_value = {"results": []}
        mock_client.blocks.children.append.return_value = {}
        
        importer = ConversationImporter("test_token", "db_123")
        conversation = self.create_sample_conversation()
        
        stats = importer.import_conversations([conversation], mode="update")
        
        assert stats["updated"] == 1
        assert stats["errors"] == 0
        mock_client.pages.update.assert_called_once()
    
    @patch('src.notion.database_manager.Client')
    def test_import_existing_conversation_skip_mode(self, mock_client_class):
        """Test skipping existing conversation in create_only mode"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock existing conversation found
        mock_client.databases.query.return_value = {
            "results": [{"id": "existing_page_123"}]
        }
        
        importer = ConversationImporter("test_token", "db_123")
        conversation = self.create_sample_conversation()
        
        stats = importer.import_conversations([conversation], mode="create_only")
        
        assert stats["skipped"] == 1
        assert stats["created"] == 0
        assert stats["updated"] == 0
    
    @patch('src.notion.database_manager.Client')
    def test_dry_run_mode(self, mock_client_class):
        """Test dry run mode"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        importer = ConversationImporter("test_token", "db_123")
        conversation = self.create_sample_conversation()
        
        stats = importer.import_conversations([conversation], dry_run=True)
        
        assert stats["created"] == 1
        assert stats["errors"] == 0
        # Should not make any actual API calls
        mock_client.databases.query.assert_not_called()
        mock_client.pages.create.assert_not_called()
    
    @patch('src.notion.database_manager.Client')
    def test_build_page_properties(self, mock_client_class):
        """Test building page properties for Notion"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        importer = ConversationImporter("test_token", "db_123")
        conversation = self.create_sample_conversation()
        
        properties = importer._build_page_properties(conversation)
        
        assert properties["タイトル"]["title"][0]["text"]["content"] == "Test Conversation"
        assert properties["トピック"]["select"]["name"] == "技術相談"
        assert properties["ステータス"]["select"]["name"] == "完了"
        assert properties["参考になった度"]["select"]["name"] == "⭐⭐⭐"
        assert properties["メッセージ数"]["number"] == 2
        assert properties["会話ID"]["rich_text"][0]["text"]["content"] == "test_conv_123"
    
    @patch('src.notion.database_manager.Client')
    def test_build_page_content(self, mock_client_class):
        """Test building page content blocks"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        importer = ConversationImporter("test_token", "db_123")
        conversation = self.create_sample_conversation()
        
        children = importer._build_page_content(conversation)
        
        assert len(children) > 0
        # Should have header, metadata, and message blocks
        assert any(block["type"] == "heading_2" for block in children)
        assert any(block["type"] == "callout" for block in children)
        assert any(block["type"] == "heading_3" for block in children)
        assert any(block["type"] == "paragraph" for block in children)
    
    @patch('src.notion.database_manager.Client')
    def test_batch_import(self, mock_client_class):
        """Test batch import functionality"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock no existing conversations
        mock_client.databases.query.return_value = {"results": []}
        mock_client.pages.create.return_value = {"id": "new_page"}
        
        importer = ConversationImporter("test_token", "db_123")
        
        # Create multiple conversations
        conversations = [self.create_sample_conversation() for _ in range(5)]
        for i, conv in enumerate(conversations):
            conv.conversation_id = f"test_conv_{i}"
        
        stats = importer.batch_import(conversations, batch_size=2)
        
        assert stats["total"] == 5
        assert stats["created"] == 5
        assert stats["errors"] == 0