import json
import logging
from typing import Optional, Dict, Any, Tuple
from app.services.mcp_client import MCPClient
from app.services.schema_service import SchemaService
from app.services.sampling_service import SamplingService
from app.models.query import (
    QueryResponse, ModelPreferences, QueryResult,
    MetabaseQuestion
)
from app.core.exceptions import QueryError, MCPError
from app.utils.logging import logger, log_execution_time
from app.core.mcp.session import MCPSession

class QueryService:
    def __init__(
        self,
        mcp_client: MCPClient,
        schema_service: SchemaService,
        sampling_service: SamplingService
    ):
        self.mcp_client = mcp_client
        self.schema_service = schema_service
        self.sampling_service = sampling_service

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
            except json.JSONDecodeError as e:
                # Check if it's a MySQL error tuple
                if result_text.startswith('(') and 'Unknown column' in result_text:
                    if retry:
                        return result_text, True
                    else:
                        raise QueryError(f"MySQL Error: {result_text}")
                raise QueryError(f"Failed to parse query result: {str(e)}")
                
        except Exception as e:
            if retry:
                return str(e), True
            raise QueryError(f"Query execution failed: {str(e)}")

    @log_execution_time
    async def process_query(
        self,
        question: str,
        model_preferences: Optional[ModelPreferences] = None
    ) -> QueryResponse:
        """Process a natural language query using MCP primitives"""
        
        async def process_with_session(session):
            try:
                # Get schema
                logger.info("Fetching schema...")
                schema = await self.schema_service.get_schema(session)
                
                # Initial SQL and visualization generation
                logger.info("Generating SQL and visualization settings...")
                sql_query, explanation, thought_process, metabase_question = (
                    await self.sampling_service.generate_sql_and_viz(
                        session,
                        question,
                        schema,
                        model_preferences
                    )
                )
                
                # Execute query with potential refinement
                logger.info(f"Executing SQL: {sql_query}")
                result, needs_refinement = await self._execute_query(session, sql_query)
                
                if needs_refinement:
                    # Get refined SQL based on error
                    logger.info(f"Refining SQL due to error: {result}")
                    refined_sql, explanation, thought_process = await self.sampling_service.refine_sql(
                        session,
                        sql_query,
                        result,
                        schema
                    )
                    
                    logger.info(f"Executing refined SQL: {refined_sql}")
                    result, _ = await self._execute_query(session, refined_sql, retry=False)
                    sql_query = refined_sql
                    
                    # Update Metabase question with refined SQL
                    metabase_question.dataset_query["native"]["query"] = refined_sql

                return QueryResponse(
                    sql=sql_query,
                    result=QueryResult(**result),
                    explanation=explanation,
                    thought_process=thought_process,
                    metabase_question=metabase_question
                )
            except Exception as e:
                logger.error(f"Error processing query: {str(e)}", exc_info=True)
                if isinstance(e, QueryError):
                    raise
                raise QueryError(str(e))

        try:
            return await self.mcp_client.with_session(process_with_session)
        except Exception as e:
            logger.error(f"Error in process_query: {str(e)}", exc_info=True)
            if isinstance(e, (MCPError, QueryError)):
                raise
            raise QueryError(f"Failed to process query: {str(e)}")

    @log_execution_time
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get available MCP capabilities"""
        
        async def get_caps(session):
            try:
                prompts = await session.list_prompts()
                schema = await self.schema_service.get_schema(session)
                
                # Also get Metabase visualization capabilities
                visualization_types = {
                    "time_series": ["line", "area", "bar"],
                    "comparisons": ["bar", "pie", "funnel"],
                    "distributions": ["histogram", "scatter"],
                    "relationships": ["scatter", "bubble"],
                    "composition": ["pie", "stacked_bar", "stacked_area"],
                    "geographical": ["map"]
                }
                logging.info(prompts)
                
                return {
                    "prompts": [prompt for prompt in prompts],
                    "schema": schema,
                    "visualizations": visualization_types,
                    "features": {
                        "supports_aggregations": True,
                        "supports_custom_fields": True,
                        "supports_drill_through": True,
                        "supports_filters": True,
                        "supports_parameters": True
                    }
                }
            except Exception as e:
                logger.error(f"Error in get_caps: {str(e)}", exc_info=True)
                raise
            
        try:
            return await self.mcp_client.with_session(get_caps)
        except Exception as e:
            logger.error(f"Error in get_capabilities: {str(e)}", exc_info=True)
            raise MCPError(f"Failed to get capabilities: {str(e)}")

    async def preview_visualization(
        self,
        question: str,
        sql: str,
        viz_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Preview how a visualization would look with sample data"""
        
        async def preview(session):
            try:
                # Execute query with limit to get sample data
                sample_sql = f"{sql} LIMIT 100"
                result, _ = await self._execute_query(session, sample_sql, retry=False)
                
                # Create preview information
                return {
                    "sample_data": result,
                    "visualization": {
                        "type": viz_settings.get("display", "table"),
                        "settings": viz_settings.get("visualization_settings", {}),
                        "columns": result.get("columns", []),
                        "row_count": len(result.get("rows", [])),
                    }
                }
            except Exception as e:
                logger.error(f"Error generating preview: {str(e)}", exc_info=True)
                raise QueryError(f"Failed to generate preview: {str(e)}")
                
        return await self.mcp_client.with_session(preview)