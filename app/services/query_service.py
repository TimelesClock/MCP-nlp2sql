# query_service.py

from typing import Optional, Dict, Any, Tuple, List
import json
from app.core.exceptions import QueryError, MCPError
from app.core.mcp.session import MCPSession
from app.utils.logging import logger, log_execution_time
from app.models.query import (
    Message, QueryResponse, ModelPreferences, QueryResult,
    ToolType, ToolCall, MetabaseQuestion
)
from .mcp_client import BaseMCPClient
from .schema_service import SchemaService
from .sampling_service import SamplingService


class QueryService:
    def __init__(self, config_path: str):
        """Initialize QueryService with configuration path"""
        self.client = BaseMCPClient(config_path)
        self.schema_service = SchemaService(self.client)
        self.sampling_service = SamplingService(api_provider="openai")

    async def _execute_query(
        self,
        session: MCPSession,
        sql: str,
        retry: bool = True
    ) -> Tuple[Dict[str, Any], bool]:
        """Execute a query and handle errors"""
        try:
            result = await session.call_tool(
                "query_database",
                {"query": sql}
            )
            
            if not result.content:
                raise QueryError("No result content returned from query")
            
            result_text = next(
                (content.text for content in result.content 
                if hasattr(content, 'text')),
                None
            )
            
            if not result_text:
                raise QueryError("No text content in query result")

            try:
                return json.loads(result_text), False
            except json.JSONDecodeError:
                if result_text.startswith('(') and 'Unknown column' in result_text:
                    if retry:
                        return result_text, True
                    else:
                        raise QueryError(f"MySQL Error: {result_text}")
                raise QueryError("Failed to parse query result")
                
        except Exception as e:
            if retry:
                return str(e), True
            raise QueryError(f"Query execution failed: {str(e)}")

    @log_execution_time
    async def process_query(
        self,
        server_name: str,
        question: str,
        database_name: str,
        model_preferences: Optional[ModelPreferences] = None,
        message_history: Optional[List[Message]] = None,
        type: Optional[str] = None
    ) -> QueryResponse:
        """Process a natural language query using MCP primitives"""
        
        async def process_with_session(session):
            try:
                logger.info("Fetching schema...")
                schema = await self.schema_service.get_schema(session)
                
                logger.info("Processing with sampling service...")
                response = await self.sampling_service.process_query(
                    session=session,
                    question=question,
                    database_name=database_name,
                    schema=schema,
                    model_preferences=model_preferences,
                    message_history=message_history,
                    type=type
                )
            
                return QueryResponse(
                    explanation=response.explanation,
                    thought_process=response.thought_process,
                    tool_calls=response.tool_calls,
                    raw_llm_response=response.raw_llm_response
                )

            except Exception as e:
                logger.error(f"Error processing query: {str(e)}")
                if isinstance(e, QueryError):
                    raise
                raise QueryError(str(e))

        try:
            return await self.client.with_session(server_name, process_with_session)
        except Exception as e:
            logger.error(f"Error in process_query: {str(e)}")
            if isinstance(e, (MCPError, QueryError)):
                raise
            raise QueryError(f"Failed to process query: {str(e)}")

    @log_execution_time
    async def get_capabilities(self, server_name: str) -> Dict[str, Any]:
        """Get available MCP capabilities for a specific server"""
        
        async def get_caps(session):
            try:
                prompts = await session.list_prompts()
                schema = await self.schema_service.get_schema(session)
                
                visualization_types = {
                    "time_series": ["line", "bar", "combo", "area", "waterfall", "trend"],
                    "comparisons": ["bar", "row", "pie", "funnel"],
                    "distributions": ["scatter"],
                    "single_value": ["progress", "gauge", "number"],
                    "tabular": ["table", "pivot table"],
                    "geographical": ["map"],
                    "composition": ["pie", "waterfall", "stacked_bar", "stacked_area"]
                }
                logger.info(prompts)
                
                return {
                    "prompts": [prompt for prompt in prompts],
                    "schema": schema,
                    "visualizations": visualization_types,
                    "features": {
                        "supports_aggregations": True,
                        "supports_custom_fields": True,
                        "supports_drill_through": True,
                        "supports_filters": True,
                        "supports_parameters": True,
                        "supports_dashboard": True
                    }
                }
            except Exception as e:
                logger.error(f"Error in get_caps: {str(e)}")
                raise
            
        try:
            return await self.client.with_session(server_name, get_caps)
        except Exception as e:
            logger.error(f"Error in get_capabilities: {str(e)}")
            raise MCPError(f"Failed to get capabilities: {str(e)}")

    def list_servers(self) -> Dict[str, Any]:
        """List all available MCP servers with their configurations"""
        try:
            servers = self.client.server_manager.list_servers()
            server_info = {}
            
            for server_name in servers:
                config = self.client.server_manager.get_server_config(server_name)
                server_info[server_name] = {
                    "command": config.command,
                    "args": config.args,
                    "env_vars": list(config.env.keys()) if config.env else []
                }
            
            return {
                "servers": servers,
                "server_details": server_info,
                "default_server": "mysql"
            }
        except Exception as e:
            logger.error(f"Error listing servers: {str(e)}")
            raise MCPError(f"Failed to list servers: {str(e)}")