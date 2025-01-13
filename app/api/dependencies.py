# app/api/dependencies.py

import os
from typing import Dict
from fastapi import Depends, Security, HTTPException
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from app.db.database import DB
from app.services.query_service import QueryService
from app.services.schema_service import SchemaService
from app.services.sampling_service import SamplingService
from app.config import settings

# API Key headers
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)
ADMIN_KEY = settings.ADMIN_KEY

if not ADMIN_KEY:
    raise ValueError("ADMIN_KEY environment variable must be set")

# Config path for MCP servers
DEFAULT_CONFIG_PATH = os.path.expanduser("mcp_config.json")
MCP_CONFIG_PATH = os.getenv("MCP_CONFIG_PATH", DEFAULT_CONFIG_PATH)

# Cached services
_query_services: Dict[str, QueryService] = {}

async def verify_api_key(
    api_key: str = Security(api_key_header)
) -> str:
    """Verify regular API key for API access"""
    if not api_key:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="No API key provided"
        )
    
    name = DB.verify_key(api_key)
    if not name:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid or inactive API key"
        )
    return name

async def verify_admin_key(
    admin_key: str = Security(admin_key_header)
) -> str:
    """Verify admin key for admin operations"""
    if not admin_key or admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid admin key"
        )
    return admin_key

def get_query_service(server_name: str = "mysql") -> QueryService:
    """Get or create a QueryService instance for a specific server"""
    if server_name not in _query_services:
        _query_services[server_name] = QueryService(MCP_CONFIG_PATH)
    return _query_services[server_name]

def get_schema_service(query_service: QueryService = Depends(get_query_service)) -> SchemaService:
    """Get SchemaService instance"""
    return query_service.schema_service

def get_sampling_service(query_service: QueryService = Depends(get_query_service)) -> SamplingService:
    """Get SamplingService instance"""
    return query_service.sampling_service