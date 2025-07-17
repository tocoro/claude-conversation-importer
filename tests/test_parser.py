"""
Tests for conversation parser module
"""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from src.parsers.conversations_parser import (
    ConversationsParser, 
    ParsedConversation, 
    ParsedMessage,
    validate_json_structure,
    detect_json_schema
)


class TestConversationsParser:
    """Test cases for ConversationsParser"""
    
    def test_parse_valid_json(self):
        """Test parsing valid conversations.json"""
        sample_data = {
            "conversations": [
                {
                    "id": "test_001",
                    "title": "Test Conversation",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T11:00:00Z",
                    "messages": [
                        {
                            "role": "human",
                            "content": "Hello, this is a test message.",
                            "timestamp": "2024-01-15T10:30:00Z"
                        },
                        {
                            "role": "assistant",
                            "content": "Hello! I'm here to help you.",
                            "timestamp": "2024-01-15T10:31:00Z"
                        }
                    ]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_data, f)
            temp_path = f.name
        
        try:
            parser = ConversationsParser(temp_path)
            conversations = parser.parse()
            
            assert len(conversations) == 1
            conv = conversations[0]
            
            assert conv.conversation_id == "test_001"
            assert conv.title == "Test Conversation"
            assert len(conv.messages) == 2
            assert conv.message_count == 2
            assert conv.messages[0].role == "human"
            assert conv.messages[1].role == "assistant"
            
        finally:
            Path(temp_path).unlink()
    
    def test_parse_direct_list_format(self):
        """Test parsing conversations as direct list format"""
        sample_data = [
            {
                "id": "test_002",
                "title": "Direct List Test",
                "created_at": "2024-01-15T10:30:00Z",
                "messages": [
                    {
                        "role": "human",
                        "content": "Test message in direct list format"
                    }
                ]
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_data, f)
            temp_path = f.name
        
        try:
            parser = ConversationsParser(temp_path)
            conversations = parser.parse()
            
            assert len(conversations) == 1
            assert conversations[0].conversation_id == "test_002"
            
        finally:
            Path(temp_path).unlink()
    
    def test_message_role_normalization(self):
        """Test that message roles are properly normalized"""
        sample_data = {
            "conversations": [
                {
                    "id": "test_003",
                    "title": "Role Test",
                    "messages": [
                        {"role": "user", "content": "User message"},
                        {"role": "ai", "content": "AI message"},
                        {"role": "human", "content": "Human message"},
                        {"role": "assistant", "content": "Assistant message"}
                    ]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_data, f)
            temp_path = f.name
        
        try:
            parser = ConversationsParser(temp_path)
            conversations = parser.parse()
            
            conv = conversations[0]
            roles = [msg.role for msg in conv.messages]
            
            assert roles == ["human", "assistant", "human", "assistant"]
            
        finally:
            Path(temp_path).unlink()
    
    def test_topic_classification(self):
        """Test automatic topic classification"""
        sample_data = {
            "conversations": [
                {
                    "id": "test_004",
                    "title": "Programming Help",
                    "messages": [
                        {
                            "role": "human", 
                            "content": "Pythonでプログラミングのエラーが発生しています。APIの実装でデバッグが必要です。"
                        },
                        {
                            "role": "assistant",
                            "content": "プログラミングのエラーについてお手伝いします。コードを確認させてください。"
                        }
                    ]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_data, f)
            temp_path = f.name
        
        try:
            parser = ConversationsParser(temp_path)
            conversations = parser.parse()
            
            # Should be classified as technical consultation due to programming keywords
            assert conversations[0].topic == "技術相談"
            
        finally:
            Path(temp_path).unlink()
    
    def test_file_not_found(self):
        """Test handling of non-existent file"""
        parser = ConversationsParser("non_existent_file.json")
        
        with pytest.raises(FileNotFoundError):
            parser.parse()
    
    def test_invalid_json(self):
        """Test handling of invalid JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json content")
            temp_path = f.name
        
        try:
            parser = ConversationsParser(temp_path)
            
            with pytest.raises(ValueError, match="Invalid JSON format"):
                parser.parse()
                
        finally:
            Path(temp_path).unlink()
    
    def test_get_file_stats(self):
        """Test file statistics generation"""
        sample_data = {
            "conversations": [
                {
                    "id": "test_005",
                    "title": "Stats Test 1",
                    "created_at": "2024-01-15T10:30:00Z",
                    "messages": [{"role": "human", "content": "プログラミングについて教えて"}] * 5
                },
                {
                    "id": "test_006", 
                    "title": "Stats Test 2",
                    "created_at": "2024-01-16T10:30:00Z",
                    "messages": [{"role": "human", "content": "作業効率化について"}] * 3
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_data, f)
            temp_path = f.name
        
        try:
            parser = ConversationsParser(temp_path)
            stats = parser.get_file_stats()
            
            assert stats["total_conversations"] == 2
            assert stats["total_messages"] == 8
            assert stats["average_messages_per_conversation"] == 4.0
            assert "技術相談" in stats["topic_distribution"]
            assert "作業効率化" in stats["topic_distribution"]
            
        finally:
            Path(temp_path).unlink()


class TestValidationFunctions:
    """Test validation utility functions"""
    
    def test_validate_valid_json_structure(self):
        """Test validation of valid JSON structure"""
        sample_data = {"conversations": [{"id": "test", "messages": []}]}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_data, f)
            temp_path = f.name
        
        try:
            is_valid, errors = validate_json_structure(temp_path)
            assert is_valid is True
            assert len(errors) == 0
            
        finally:
            Path(temp_path).unlink()
    
    def test_validate_invalid_json_structure(self):
        """Test validation of invalid JSON structure"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json")
            temp_path = f.name
        
        try:
            is_valid, errors = validate_json_structure(temp_path)
            assert is_valid is False
            assert len(errors) > 0
            assert "Invalid JSON" in errors[0]
            
        finally:
            Path(temp_path).unlink()
    
    def test_detect_json_schema(self):
        """Test JSON schema detection"""
        sample_data = {
            "conversations": [
                {
                    "id": "test",
                    "title": "Test",
                    "messages": [
                        {"role": "human", "content": "test"}
                    ]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_data, f)
            temp_path = f.name
        
        try:
            schema = detect_json_schema(temp_path)
            
            assert schema["root_type"] == "dict"
            assert schema["estimated_conversations"] == 1
            assert "id" in schema["sample_keys"]
            assert "title" in schema["sample_keys"]
            assert schema["message_structure"]["message_key"] == "messages"
            
        finally:
            Path(temp_path).unlink()


class TestParsedConversation:
    """Test ParsedConversation data class"""
    
    def test_post_init_processing(self):
        """Test post-initialization processing"""
        messages = [
            ParsedMessage(role="human", content="プログラミングについて教えて"),
            ParsedMessage(role="assistant", content="プログラミングについて説明します")
        ]
        
        conv = ParsedConversation(
            conversation_id="test",
            title="Test Conversation",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            messages=messages,
            message_count=len(messages)
        )
        
        # Should auto-generate summary and classify topic
        assert conv.summary != ""
        assert conv.topic == "学習・調査"  # Should be classified as learning due to "教えて" content
        assert conv.status == "完了"
        assert conv.rating == "⭐⭐⭐"