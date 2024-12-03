from fastapi import APIRouter, Depends, HTTPException
from app.models.query import NLQuery, QueryResponse
from app.services.query_service import QueryService
from app.api.dependencies import get_query_service
from app.utils.logging import logger

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def process_natural_language_query(
    query: NLQuery,
    query_service: QueryService = Depends(get_query_service)
):
    """Process a natural language query and return SQL results"""
    try:
        a = await query_service.process_query(
            query.question,
            query.model_preferences
        )
        print(a)
        return a
    except Exception as e:
        logger.exception("Failed to process query",e)
        raise HTTPException(status_code=400, detail=str(e))

# TOFIX
@router.get("/capabilities")
async def get_capabilities(
    query_service: QueryService = Depends(get_query_service)
):
    """Get available MCP capabilities"""
    return await query_service.get_capabilities()