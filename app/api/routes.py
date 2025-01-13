# app/api/routers/query.py

from fastapi import APIRouter, Depends, HTTPException, Query
from app.models.query import NLQuery, QueryResponse
from app.services.query_service import QueryService
from app.api.dependencies import get_query_service, verify_api_key
from app.utils.logging import logger

router = APIRouter()

@router.get("/")
async def health_check():
    return {"status": "ok"}

@router.post("/query", response_model=QueryResponse)
async def process_natural_language_query(
    query: NLQuery,
    server_name: str = Query(default="mysql", description="MCP server name to use"),
    client_id: str = Depends(verify_api_key),
    query_service: QueryService = Depends(get_query_service)
):
    """Process a natural language query and return SQL results"""
    try:
        messages = None
        if query.message_history:
            try:
                # Process message history including tool calls
                messages = [msg for msg in query.message_history]
                logger.info(f"Processed {len(messages)} messages from history")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
                
        final = await query_service.process_query(
            server_name=server_name,
            question=query.question,
            database_name=query.database_name,
            model_preferences=query.model_preferences,
            message_history=messages,
            type=query.type
        )
        
        logger.info(f"Query processed successfully for client {client_id} using server {server_name}")
        return final
        
    except Exception as e:
        logger.exception(f"Failed to process query for client {client_id} using server {server_name}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/capabilities")
async def get_capabilities(
    server_name: str = Query(default="mysql", description="MCP server name to use"),
    client_id: str = Depends(verify_api_key),
    query_service: QueryService = Depends(get_query_service)
):
    """Get available MCP capabilities for a specific server"""
    try:
        capabilities = await query_service.get_capabilities(server_name)
        logger.info(f"Retrieved capabilities for client {client_id} using server {server_name}")
        return capabilities
    except Exception as e:
        logger.exception(f"Failed to get capabilities for client {client_id} using server {server_name}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/servers")
async def list_servers(
    client_id: str = Depends(verify_api_key),
    query_service: QueryService = Depends(get_query_service)
):
    """List available MCP servers"""
    try:
        servers = query_service.list_servers()
        return {"servers": servers}
    except Exception as e:
        logger.exception(f"Failed to list servers for client {client_id}")
        raise HTTPException(status_code=400, detail=str(e))