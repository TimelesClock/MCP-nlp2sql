# schema_service.py

import json
from typing import Dict, Any, List, Set
import mcp.types as types
from app.core.exceptions import SchemaError
from app.utils.logging import logger
from .mcp_client import BaseMCPClient


class SchemaService:
    def __init__(self, client: BaseMCPClient):
        self.client = client
        self.schema_cache: Dict[str, Any] = {}
        self.column_cache: Dict[str, Set[str]] = {}

    async def get_schema(self, session) -> Dict[str, Any]:
        """Get database schema using resources or tools"""
        if self.schema_cache:
            return self.schema_cache

        try:
            # Try to get schema using tools first as it's more reliable
            schema = await self._get_schema_from_tools(session)
            if schema:
                self._cache_column_names(schema)
                self.schema_cache = schema
                return schema

            # Fallback to resources
            schema = await self._get_schema_from_resources(session)
            self._cache_column_names(schema)
            self.schema_cache = schema
            return schema
            
        except Exception as e:
            logger.error(f"Failed to fetch schema: {str(e)}")
            raise SchemaError(f"Failed to fetch schema: {str(e)}")

    def validate_column_name(self, column: str) -> bool:
        """Check if a column exists in any table"""
        for columns in self.column_cache.values():
            if column in columns:
                return True
        return False

    def get_table_for_column(self, column: str) -> str:
        """Get the table name for a given column"""
        for table, columns in self.column_cache.items():
            if column in columns:
                return table
        return None

    def _cache_column_names(self, schema: Dict[str, Any]) -> None:
        """Cache column names from schema"""
        self.column_cache = {}
        for table_name, table_data in schema.get("tables", {}).items():
            self.column_cache[table_name] = {
                col["Field"] for col in table_data
            }

    async def _get_schema_from_tools(self, session) -> Dict[str, Any]:
        """Get schema using tools"""
        schema = {}
        
        # List tables
        tables_result = await session.call_tool("list_tables", {})
        if not tables_result.content:
            raise SchemaError("Failed to get tables list")
        logger.info(f"Tables result: {tables_result.content}")
            
        tables_text = next(
            (content.text for content in tables_result.content 
             if isinstance(content, types.TextContent)),
            None
        )
        if not tables_text:
            raise SchemaError("No text content in tables result")
            
        try:
            tables = json.loads(tables_text)
        except json.JSONDecodeError as e:
            raise SchemaError(f"Failed to parse tables JSON: {str(e)}")
        
        # Get structure for each table
        for table in tables:
            try:
                struct_result = await session.call_tool(
                    "describe_table",
                    {"table_name": table}
                )
                
                if not struct_result.content:
                    continue
                    
                struct_text = next(
                    (content.text for content in struct_result.content 
                     if isinstance(content, types.TextContent)),
                    None
                )
                if not struct_text:
                    continue
                    
                schema[table] = json.loads(struct_text)
                
            except Exception as e:
                logger.error(f"Error getting schema for table {table}: {str(e)}")
                continue
            
        return {
            "tables": schema,
            "relationships": self._infer_relationships(schema)
        }

    async def _get_schema_from_resources(self, session) -> Dict[str, Any]:
        """Get schema from resources"""
        schema = {}
        
        try:
            # List available resources
            resources = await session.list_resources()
            
            # Read each resource
            for resource in resources:
                if not hasattr(resource, 'uri') or not resource.uri:
                    continue
                    
                content_result = await session.read_resource(resource.uri)
                if not content_result.content:
                    continue
                
                content_text = next(
                    (content.text for content in content_result.content 
                     if isinstance(content, types.TextContent)),
                    None
                )
                if not content_text:
                    continue
                    
                try:
                    table_name = resource.uri.split('/')[-1]
                    schema[table_name] = json.loads(content_text)
                except (json.JSONDecodeError, IndexError):
                    continue
                    
            return {
                "tables": schema,
                "relationships": self._infer_relationships(schema)
            }
            
        except Exception as e:
            raise SchemaError(f"Failed to get schema from resources: {str(e)}")

    def _infer_relationships(self, schema: Dict[str, Any]) -> List[Dict[str, str]]:
        """Infer relationships between tables based on column names and types"""
        relationships = []
        
        for table_name, table_data in schema.items():
            for column in table_data:
                # Look for potential foreign keys
                if (column.get('Key', '').upper() == 'MUL' or 
                    '_id' in column.get('Field', '').lower()):
                    # Try to find the referenced table
                    possible_table = column['Field'].replace('_id', '')
                    if possible_table in schema:
                        relationships.append({
                            "from_table": table_name,
                            "to_table": possible_table,
                            "type": "foreign_key",
                            "from_column": column['Field'],
                            "to_column": "id"  # Assuming standard primary key name
                        })
        
        return relationships