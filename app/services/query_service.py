import json
from typing import Optional, Dict, Any, Tuple
from app.services.mcp_client import MCPClient
from app.services.schema_service import SchemaService
from app.services.sampling_service import SamplingService
from app.models.query import QueryResponse, ModelPreferences, QueryResult
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
                
                # Initial SQL generation
                logger.info("Generating SQL...")
                sql_query, explanation, thought_process = await self.sampling_service.generate_sql(
                    session,
                    question,
                    schema,
                    model_preferences
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

                return QueryResponse(
                    sql=sql_query,
                    result=QueryResult(**result),
                    explanation=explanation,
                    thought_process=thought_process
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
                
                return {
                    "prompts": [prompt.dict() for prompt in prompts],
                    "schema": schema
                }
            except Exception as e:
                logger.error(f"Error in get_caps: {str(e)}", exc_info=True)
                raise
            
        try:
            return await self.mcp_client.with_session(get_caps)
        except Exception as e:
            logger.error(f"Error in get_capabilities: {str(e)}", exc_info=True)
            raise MCPError(f"Failed to get capabilities: {str(e)}")