"""
Parser for Claude conversations.json files
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from dateutil.parser import parse as parse_date

from config.settings import TOPIC_KEYWORDS


@dataclass
class ParsedMessage:
    """Represents a single message in a conversation"""
    role: str  # "human" or "assistant"
    content: str
    timestamp: Optional[datetime] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ParsedConversation:
    """Represents a parsed conversation from conversations.json"""
    conversation_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ParsedMessage]
    message_count: int
    summary: str = ""
    topic: str = "その他"
    status: str = "完了"
    rating: str = "⭐⭐⭐"
    
    def __post_init__(self):
        """Post-initialization processing"""
        if not self.summary:
            self.summary = self.generate_summary()
        
        if self.topic == "その他":
            self.topic = self.classify_topic()
    
    def generate_summary(self) -> str:
        """Generate a summary for the conversation"""
        if not self.messages:
            return "Empty conversation"
        
        # Get first human message as potential summary
        first_human_msg = None
        for msg in self.messages:
            if msg.role == "human":
                first_human_msg = msg.content
                break
        
        if not first_human_msg:
            return self.title
        
        # Truncate to reasonable length
        summary = first_human_msg[:500]
        if len(first_human_msg) > 500:
            summary += "..."
            
        return summary
    
    def classify_topic(self) -> str:
        """Classify conversation topic based on content"""
        # Combine all message content
        all_content = " ".join([msg.content for msg in self.messages])
        all_content = all_content.lower()
        
        # Count keyword matches for each topic
        topic_scores = {}
        for topic, keywords in TOPIC_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in all_content)
            if score > 0:
                topic_scores[topic] = score
        
        if topic_scores:
            # Return topic with highest score
            return max(topic_scores.items(), key=lambda x: x[1])[0]
        
        return "その他"


class ConversationsParser:
    """Parser for Claude conversations.json files"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.raw_data: Optional[Dict[str, Any]] = None
        
    def parse(self) -> List[ParsedConversation]:
        """Parse the conversations.json file"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")
            
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.raw_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        
        return self._extract_conversations()
    
    def _extract_conversations(self) -> List[ParsedConversation]:
        """Extract conversations from raw JSON data"""
        conversations = []
        
        # Handle different possible JSON structures
        if isinstance(self.raw_data, list):
            # Direct list of conversations (Claude official format)
            raw_conversations = self.raw_data
        elif isinstance(self.raw_data, dict):
            # Check common keys that might contain conversations
            if "conversations" in self.raw_data:
                raw_conversations = self.raw_data["conversations"]
            elif "data" in self.raw_data:
                raw_conversations = self.raw_data["data"]
            else:
                # Assume the dict values are conversations
                raw_conversations = list(self.raw_data.values())
        else:
            raise ValueError("Unsupported JSON structure")
        
        for conv_data in raw_conversations:
            try:
                conversation = self._parse_single_conversation(conv_data)
                if conversation:
                    conversations.append(conversation)
            except Exception as e:
                print(f"Warning: Failed to parse conversation: {e}")
                continue
                
        return conversations
    
    def _parse_single_conversation(self, conv_data: Dict[str, Any]) -> Optional[ParsedConversation]:
        """Parse a single conversation from raw data"""
        # Extract basic information (Claude official format)
        conv_id = self._extract_field(conv_data, ["uuid", "id", "conversation_id"])
        title = self._extract_field(conv_data, ["name", "title", "subject"])
        
        if not conv_id:
            return None
            
        # Extract timestamps
        created_at = self._extract_timestamp(conv_data, ["created_at", "created", "start_time"])
        updated_at = self._extract_timestamp(conv_data, ["updated_at", "updated", "last_modified"]) or created_at
        
        # Extract messages
        messages = self._extract_messages(conv_data)
        
        if not messages:
            return None
            
        return ParsedConversation(
            conversation_id=conv_id,
            title=title or f"Conversation {conv_id[:8]}",
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
            messages=messages,
            message_count=len(messages)
        )
    
    def _extract_field(self, data: Dict[str, Any], possible_keys: List[str]) -> Optional[str]:
        """Extract a field from data using multiple possible keys"""
        for key in possible_keys:
            if key in data and data[key]:
                return str(data[key])
        return None
    
    def _extract_timestamp(self, data: Dict[str, Any], possible_keys: List[str]) -> Optional[datetime]:
        """Extract and parse timestamp from data"""
        for key in possible_keys:
            if key in data and data[key]:
                try:
                    if isinstance(data[key], (int, float)):
                        # Unix timestamp
                        return datetime.fromtimestamp(data[key])
                    else:
                        # String timestamp
                        return parse_date(str(data[key]))
                except (ValueError, TypeError):
                    continue
        return None
    
    def _extract_messages(self, conv_data: Dict[str, Any]) -> List[ParsedMessage]:
        """Extract messages from conversation data"""
        messages = []
        
        # Look for messages in common locations (Claude official format)
        messages_data = None
        for key in ["chat_messages", "messages", "turns", "exchanges", "history"]:
            if key in conv_data and conv_data[key]:
                messages_data = conv_data[key]
                break
        
        if not messages_data:
            return []
        
        for msg_data in messages_data:
            try:
                message = self._parse_single_message(msg_data)
                if message:
                    messages.append(message)
            except Exception as e:
                print(f"Warning: Failed to parse message: {e}")
                continue
                
        return messages
    
    def _parse_single_message(self, msg_data: Dict[str, Any]) -> Optional[ParsedMessage]:
        """Parse a single message from raw data"""
        # Extract role (Claude official format)
        role = self._extract_field(msg_data, ["sender", "role", "author", "type"])
        if not role:
            return None
            
        # Normalize role names
        if role.lower() in ["user", "human"]:
            role = "human"
        elif role.lower() in ["assistant", "ai", "claude"]:
            role = "assistant"
        
        # Extract content (Claude official format: use "text" field)
        content = self._extract_field(msg_data, ["text", "content", "message", "body"])
        if not content:
            return None
        
        # Extract timestamp
        timestamp = self._extract_timestamp(msg_data, ["created_at", "timestamp", "time"])
        
        # Extract attachments
        attachments = []
        if "attachments" in msg_data and msg_data["attachments"]:
            attachments = msg_data["attachments"]
        
        return ParsedMessage(
            role=role,
            content=content,
            timestamp=timestamp,
            attachments=attachments
        )
    
    
    def get_file_stats(self) -> Dict[str, Any]:
        """Get statistics about the conversations file"""
        if not self.raw_data:
            # Load data if not already loaded
            self.parse()
        
        conversations = self._extract_conversations()
        
        total_messages = sum(conv.message_count for conv in conversations)
        
        # Date range
        dates = [conv.created_at for conv in conversations if conv.created_at]
        date_range = {
            "earliest": min(dates) if dates else None,
            "latest": max(dates) if dates else None
        }
        
        # Topic distribution
        topics = {}
        for conv in conversations:
            topics[conv.topic] = topics.get(conv.topic, 0) + 1
        
        return {
            "total_conversations": len(conversations),
            "total_messages": total_messages,
            "average_messages_per_conversation": total_messages / len(conversations) if conversations else 0,
            "date_range": date_range,
            "topic_distribution": topics,
            "file_size_mb": self.file_path.stat().st_size / (1024 * 1024)
        }


# Utility functions for the parser
def validate_json_structure(file_path: str) -> Tuple[bool, List[str]]:
    """Validate the structure of a conversations.json file"""
    errors = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return False, ["File not found"]
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    
    # Check if data has expected structure
    if not isinstance(data, (list, dict)):
        errors.append("Root element must be list or dict")
    
    if isinstance(data, dict):
        if not any(key in data for key in ["conversations", "data"]):
            if not all(isinstance(v, dict) for v in data.values()):
                errors.append("Dict values must be conversation objects")
    
    return len(errors) == 0, errors


def detect_json_schema(file_path: str) -> Dict[str, Any]:
    """Detect the schema of a conversations.json file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    
    schema_info = {
        "root_type": type(data).__name__,
        "sample_keys": [],
        "message_structure": {},
        "estimated_conversations": 0
    }
    
    # Analyze structure
    if isinstance(data, list) and data:
        schema_info["sample_keys"] = list(data[0].keys()) if isinstance(data[0], dict) else []
        schema_info["estimated_conversations"] = len(data)
        
        # Analyze message structure
        sample_conv = data[0]
        if isinstance(sample_conv, dict):
            for key in ["messages", "turns", "exchanges", "history"]:
                if key in sample_conv and sample_conv[key]:
                    messages = sample_conv[key]
                    if messages and isinstance(messages[0], dict):
                        schema_info["message_structure"] = {
                            "message_key": key,
                            "sample_message_keys": list(messages[0].keys())
                        }
                    break
    
    elif isinstance(data, dict):
        schema_info["sample_keys"] = list(data.keys())
        
        # Try to find conversations
        for key in ["conversations", "data"]:
            if key in data and isinstance(data[key], list):
                schema_info["estimated_conversations"] = len(data[key])
                if data[key] and isinstance(data[key][0], dict):
                    schema_info["sample_keys"] = list(data[key][0].keys())
                break
    
    return schema_info