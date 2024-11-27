from fastapi import Depends
from app.services.mcp_client import MCPClient
from app.services.schema_service import SchemaService
from app.services.sampling_service import SamplingService
from app.services.query_service import QueryService

def get_mcp_client():
    """Dependency for MCPClient"""
    return MCPClient()

def get_schema_service():
    """Dependency for SchemaService"""
    return SchemaService()

def get_sampling_service():
    """Dependency for SamplingService"""
    return SamplingService()

def get_query_service(
    mcp_client: MCPClient = Depends(get_mcp_client),
    schema_service: SchemaService = Depends(get_schema_service),
    sampling_service: SamplingService = Depends(get_sampling_service)
) -> QueryService:
    """Dependency for QueryService"""
    return QueryService(
        mcp_client=mcp_client,
        schema_service=schema_service,
        sampling_service=sampling_service
    )