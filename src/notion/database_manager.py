"""
Notion database management for conversation imports
"""
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from notion_client import Client
from notion_client.errors import APIResponseError

from src.parsers.conversations_parser import ParsedConversation
from config.settings import get_settings
from src.utils.translator import translate_conversation_title


class ConversationImporter:
    """Import conversations to Notion database"""
    
    def __init__(self, token: str, database_id: str):
        self.client = Client(auth=token)
        self.database_id = database_id
        self.settings = get_settings()
        
    def import_conversations(self, conversations: List[ParsedConversation], 
                           mode: str = "update", dry_run: bool = False) -> Dict[str, int]:
        """Import conversations to Notion database"""
        stats = {
            "total": len(conversations),
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }
        
        print(f"Starting import of {len(conversations)} conversations...")
        
        for i, conversation in enumerate(conversations, 1):
            try:
                print(f"Processing {i}/{len(conversations)}: {conversation.title[:50]}...")
                
                if dry_run:
                    print(f"  [DRY RUN] Would process conversation: {conversation.conversation_id}")
                    stats["created"] += 1
                    continue
                
                # Check if conversation already exists
                existing_page_id = self._check_existing_conversation(conversation.conversation_id)
                
                if existing_page_id:
                    if mode == "update":
                        success = self._update_conversation_page(existing_page_id, conversation)
                        if success:
                            stats["updated"] += 1
                            print(f"  ✅ Updated existing conversation")
                        else:
                            stats["errors"] += 1
                            print(f"  ❌ Failed to update conversation")
                    elif mode == "create_only":
                        stats["skipped"] += 1
                        print(f"  ⏭️  Skipped existing conversation")
                    elif mode == "overwrite":
                        # Delete and recreate
                        self._delete_page(existing_page_id)
                        success = self._create_conversation_page(conversation)
                        if success:
                            stats["created"] += 1
                            print(f"  ✅ Overwritten conversation")
                        else:
                            stats["errors"] += 1
                            print(f"  ❌ Failed to overwrite conversation")
                else:
                    # Create new conversation
                    success = self._create_conversation_page(conversation)
                    if success:
                        stats["created"] += 1
                        print(f"  ✅ Created new conversation")
                    else:
                        stats["errors"] += 1
                        print(f"  ❌ Failed to create conversation")
                
                # Rate limiting
                self._rate_limit_delay()
                
            except Exception as e:
                print(f"  ❌ Error processing conversation: {e}")
                stats["errors"] += 1
                continue
        
        return stats
    
    def _check_existing_conversation(self, conversation_id: str) -> Optional[str]:
        """Check if conversation already exists"""
        try:
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "会話ID",
                    "rich_text": {
                        "equals": conversation_id
                    }
                }
            )
            
            if response["results"]:
                return response["results"][0]["id"]
            return None
            
        except Exception as e:
            print(f"Error checking existing conversation: {e}")
            return None
    
    def _create_conversation_page(self, conversation: ParsedConversation) -> bool:
        """Create a new conversation page in Notion"""
        try:
            properties = self._build_page_properties(conversation)
            children = self._build_page_content(conversation)
            
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=children
            )
            
            return True
            
        except APIResponseError as e:
            print(f"API Error creating page: {e}")
            return False
        except Exception as e:
            print(f"Error creating page: {e}")
            return False
    
    def _update_conversation_page(self, page_id: str, conversation: ParsedConversation) -> bool:
        """Update existing conversation page"""
        try:
            properties = self._build_page_properties(conversation)
            
            # Update properties
            self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            
            # Update content (clear and rebuild)
            self._clear_page_content(page_id)
            children = self._build_page_content(conversation)
            
            if children:
                self.client.blocks.children.append(
                    block_id=page_id,
                    children=children
                )
            
            return True
            
        except Exception as e:
            print(f"Error updating page: {e}")
            return False
    
    def _build_page_properties(self, conversation: ParsedConversation) -> Dict[str, Any]:
        """Build page properties for Notion"""
        # Generate Claude link URL
        claude_url = f"https://claude.ai/chat/{conversation.conversation_id}"
        
        # Generate Japanese title with translation
        japanese_title = self._get_japanese_title(conversation.title)
        
        properties = {
            "タイトル": {
                "title": [{"text": {"content": conversation.title[:2000]}}]  # Notion title limit
            },
            "邦訳タイトル": {
                "rich_text": [{"text": {"content": japanese_title[:2000]}}]
            },
            "日付": {
                "date": {"start": conversation.created_at.isoformat()}
            },
            "トピック": {
                "select": {"name": conversation.topic}
            },
            "ステータス": {
                "select": {"name": conversation.status}
            },
            "要約": {
                "rich_text": [{"text": {"content": conversation.summary[:2000]}}]  # Notion rich_text limit
            },
            "参考になった度": {
                "select": {"name": conversation.rating}
            },
            "メッセージ数": {
                "number": conversation.message_count
            },
            "会話ID": {
                "rich_text": [{"text": {"content": conversation.conversation_id}}]
            },
            "Claude会話URL": {
                "url": claude_url
            }
        }
        
        return properties
    
    def _get_japanese_title(self, title: str) -> str:
        """Get Japanese translation of title"""
        try:
            # Use settings to get API keys
            settings = get_settings()
            if settings.openai_api_key or settings.google_api_key:
                return translate_conversation_title(
                    title, 
                    openai_key=settings.openai_api_key,
                    gemini_key=settings.google_api_key
                )
            else:
                return title  # Return original if no API key
        except Exception as e:
            print(f"Translation failed for '{title}': {e}")
            return title  # Return original if translation fails
    
    def _build_page_content(self, conversation: ParsedConversation) -> List[Dict[str, Any]]:
        """Build page content blocks for conversation messages"""
        children = []
        
        # Add conversation info header
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"text": {"content": "会話履歴"}}]
            }
        })
        
        # Add metadata
        metadata_text = f"作成日: {conversation.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        metadata_text += f"更新日: {conversation.updated_at.strftime('%Y-%m-%d %H:%M')}\n"
        metadata_text += f"メッセージ数: {conversation.message_count}\n"
        metadata_text += f"会話ID: {conversation.conversation_id}"
        
        children.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"text": {"content": metadata_text}}],
                "icon": {"emoji": "📋"}
            }
        })
        
        # Add messages
        for i, message in enumerate(conversation.messages[:100]):  # Limit for performance
            # Message header
            role_emoji = "👤" if message.role == "human" else "🤖"
            timestamp_str = message.timestamp.strftime('%H:%M') if message.timestamp else ""
            
            children.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"text": {"content": f"{role_emoji} {message.role.title()} {timestamp_str}"}}]
                }
            })
            
            # Message content
            content_text = message.content[:2000]  # Notion block limit
            if len(message.content) > 2000:
                content_text += "\n\n[内容が長いため省略されました...]"
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": content_text}}]
                }
            })
            
            # Add attachments if any
            if message.attachments:
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": f"添付ファイル: {len(message.attachments)}個"}}]
                    }
                })
        
        if len(conversation.messages) > 100:
            children.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"text": {"content": f"表示制限のため最初の100メッセージのみ表示。全{conversation.message_count}メッセージ"}}],
                    "icon": {"emoji": "⚠️"}
                }
            })
        
        return children
    
    def _clear_page_content(self, page_id: str):
        """Clear existing page content"""
        try:
            # Get all blocks
            response = self.client.blocks.children.list(block_id=page_id)
            
            # Delete all blocks
            for block in response["results"]:
                try:
                    self.client.blocks.delete(block_id=block["id"])
                except:
                    pass  # Some blocks might not be deletable
                    
        except Exception as e:
            print(f"Warning: Could not clear page content: {e}")
    
    def _delete_page(self, page_id: str):
        """Delete a page"""
        try:
            self.client.pages.update(
                page_id=page_id,
                archived=True
            )
        except Exception as e:
            print(f"Error deleting page: {e}")
    
    def _rate_limit_delay(self):
        """Apply rate limiting delay"""
        time.sleep(self.settings.notion_api_delay)
    
    def batch_import(self, conversations: List[ParsedConversation], 
                    batch_size: Optional[int] = None, **kwargs) -> Dict[str, int]:
        """Import conversations in batches"""
        if batch_size is None:
            batch_size = self.settings.batch_size
        
        total_stats = {"total": 0, "created": 0, "updated": 0, "skipped": 0, "errors": 0}
        
        # Process in batches
        for i in range(0, len(conversations), batch_size):
            batch = conversations[i:i + batch_size]
            print(f"\n📦 Processing batch {i//batch_size + 1} ({len(batch)} conversations)")
            
            batch_stats = self.import_conversations(batch, **kwargs)
            
            # Aggregate stats
            for key in total_stats:
                total_stats[key] += batch_stats[key]
            
            # Show batch results
            print(f"Batch results: {batch_stats['created']} created, {batch_stats['updated']} updated, "
                  f"{batch_stats['skipped']} skipped, {batch_stats['errors']} errors")
            
            # Longer delay between batches
            if i + batch_size < len(conversations):
                print("Waiting between batches...")
                time.sleep(1.0)
        
        return total_stats