"""
Notion API client for Claude conversation importer
"""
import time
from typing import Dict, List, Optional, Any, Tuple
from notion_client import Client
from notion_client.errors import APIResponseError, RequestTimeoutError

from config.settings import get_settings, REQUIRED_PROPERTIES, SELECT_OPTIONS


class NotionConnectionTester:
    """Test Notion API connection and database access"""
    
    def __init__(self, token: str, database_id: Optional[str] = None):
        self.client = Client(auth=token)
        self.database_id = database_id
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Notion API connection and database access"""
        results = {
            "api_connection": False,
            "database_access": False,
            "database_structure": False,
            "error_message": None,
            "database_info": None
        }
        
        try:
            # Test API connection
            user_info = self.client.users.me()
            results["api_connection"] = True
            
            if self.database_id:
                # Test database access
                db_info = self.client.databases.retrieve(self.database_id)
                results["database_access"] = True
                results["database_info"] = {
                    "title": db_info.get("title", [{}])[0].get("text", {}).get("content", "Unknown"),
                    "properties": list(db_info.get("properties", {}).keys())
                }
                
                # Test database structure
                db_props = db_info.get("properties", {})
                missing_props = []
                for prop_name, prop_type in REQUIRED_PROPERTIES.items():
                    if prop_name not in db_props:
                        missing_props.append(prop_name)
                    elif db_props[prop_name]["type"] != prop_type:
                        missing_props.append(f"{prop_name} (wrong type)")
                
                results["database_structure"] = len(missing_props) == 0
                if missing_props:
                    results["error_message"] = f"Missing or incorrect properties: {missing_props}"
                    
        except APIResponseError as e:
            results["error_message"] = f"API Error: {e}"
        except Exception as e:
            results["error_message"] = f"Unexpected error: {e}"
            
        return results
    
    def list_accessible_databases(self) -> List[Dict[str, str]]:
        """List all accessible databases"""
        try:
            response = self.client.search(filter={"property": "object", "value": "database"})
            databases = []
            
            for db in response.get("results", []):
                title = "Unknown"
                if db.get("title") and len(db["title"]) > 0:
                    title = db["title"][0].get("text", {}).get("content", "Unknown")
                
                databases.append({
                    "id": db["id"],
                    "title": title,
                    "url": db.get("url", "")
                })
            
            return databases
            
        except Exception as e:
            print(f"Error listing databases: {e}")
            return []


class NotionDatabaseManager:
    """Manage Notion database operations"""
    
    def __init__(self, token: str, database_id: Optional[str] = None):
        self.client = Client(auth=token)
        self.database_id = database_id
        self.settings = get_settings()
    
    def create_database(self, parent_page_id: str, title: str = "Claude会話ログ") -> str:
        """Create a new database with the required schema"""
        from config.settings import DATABASE_SCHEMA
        
        schema = DATABASE_SCHEMA.copy()
        schema["parent"] = {"type": "page_id", "page_id": parent_page_id}
        schema["title"] = [{"text": {"content": title}}]
        
        try:
            response = self.client.databases.create(**schema)
            database_id = response["id"]
            print(f"✅ Created database: {title} (ID: {database_id})")
            return database_id
            
        except APIResponseError as e:
            raise Exception(f"Failed to create database: {e}")
    
    def validate_database_structure(self, database_id: str) -> Tuple[bool, List[str]]:
        """Validate that database has required properties"""
        try:
            db_info = self.client.databases.retrieve(database_id)
            db_props = db_info.get("properties", {})
            
            issues = []
            
            # Check required properties
            for prop_name, expected_type in REQUIRED_PROPERTIES.items():
                if prop_name not in db_props:
                    issues.append(f"Missing property: {prop_name}")
                elif db_props[prop_name]["type"] != expected_type:
                    actual_type = db_props[prop_name]["type"]
                    issues.append(f"Property '{prop_name}' has type '{actual_type}', expected '{expected_type}'")
            
            # Check select options
            for prop_name, expected_options in SELECT_OPTIONS.items():
                if prop_name in db_props and db_props[prop_name]["type"] == "select":
                    existing_options = [opt["name"] for opt in db_props[prop_name]["select"]["options"]]
                    missing_options = [opt for opt in expected_options if opt not in existing_options]
                    if missing_options:
                        issues.append(f"Property '{prop_name}' missing options: {missing_options}")
            
            return len(issues) == 0, issues
            
        except APIResponseError as e:
            return False, [f"Failed to access database: {e}"]
    
    def update_database_properties(self, database_id: str) -> bool:
        """Update database properties to match required schema"""
        try:
            db_info = self.client.databases.retrieve(database_id)
            existing_props = db_info.get("properties", {})
            
            # Add missing properties
            for prop_name, prop_type in REQUIRED_PROPERTIES.items():
                if prop_name not in existing_props:
                    self._add_database_property(database_id, prop_name, prop_type)
                    
            # Update select options
            for prop_name, options in SELECT_OPTIONS.items():
                if prop_name in existing_props and existing_props[prop_name]["type"] == "select":
                    self._update_select_options(database_id, prop_name, options)
            
            return True
            
        except Exception as e:
            print(f"Failed to update database properties: {e}")
            return False
    
    def _add_database_property(self, database_id: str, prop_name: str, prop_type: str):
        """Add a single property to database"""
        property_config = self._get_property_config(prop_name, prop_type)
        
        self.client.databases.update(
            database_id=database_id,
            properties={prop_name: property_config}
        )
        print(f"Added property: {prop_name}")
    
    def _update_select_options(self, database_id: str, prop_name: str, options: List[str]):
        """Update select options for a property"""
        # Get current options
        db_info = self.client.databases.retrieve(database_id)
        current_options = db_info["properties"][prop_name]["select"]["options"]
        existing_names = {opt["name"] for opt in current_options}
        
        # Add missing options
        new_options = current_options.copy()
        colors = ["blue", "green", "orange", "purple", "gray", "red", "yellow", "brown", "pink"]
        
        for i, option in enumerate(options):
            if option not in existing_names:
                new_options.append({
                    "name": option,
                    "color": colors[i % len(colors)]
                })
        
        if len(new_options) > len(current_options):
            self.client.databases.update(
                database_id=database_id,
                properties={
                    prop_name: {
                        "select": {"options": new_options}
                    }
                }
            )
            print(f"Updated select options for: {prop_name}")
    
    def _get_property_config(self, prop_name: str, prop_type: str) -> Dict[str, Any]:
        """Get property configuration for database schema"""
        if prop_type == "title":
            return {"title": {}}
        elif prop_type == "date":
            return {"date": {}}
        elif prop_type == "rich_text":
            return {"rich_text": {}}
        elif prop_type == "number":
            return {"number": {}}
        elif prop_type == "url":
            return {"url": {}}
        elif prop_type == "select":
            if prop_name in SELECT_OPTIONS:
                options = []
                colors = ["blue", "green", "orange", "purple", "gray", "red", "yellow"]
                for i, option in enumerate(SELECT_OPTIONS[prop_name]):
                    options.append({
                        "name": option,
                        "color": colors[i % len(colors)]
                    })
                return {"select": {"options": options}}
            else:
                return {"select": {"options": []}}
        else:
            return {"rich_text": {}}  # fallback
    
    def check_existing_conversation(self, conversation_id: str) -> Optional[str]:
        """Check if a conversation already exists in the database"""
        if not self.database_id:
            return None
            
        try:
            # Search for existing conversation by ID
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
    
    def rate_limit_delay(self):
        """Apply rate limiting delay"""
        time.sleep(self.settings.notion_api_delay)