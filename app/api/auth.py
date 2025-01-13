# app/api/auth.py
from fastapi import APIRouter, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from app.db.database import DB
import os
from starlette.status import HTTP_403_FORBIDDEN
from app.config import settings

router = APIRouter()

# Admin key header for admin operations
ADMIN_KEY = settings.ADMIN_KEY
if not ADMIN_KEY:
    raise ValueError("ADMIN_KEY environment variable must be set")

admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=True)

async def verify_admin_key(admin_key: str = Security(admin_key_header)):
    if admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid admin key"
        )
    return admin_key

@router.post("/api-keys/{name}")
async def create_api_key(
    name: str,
    _: str = Security(verify_admin_key)  # Requires admin key
):
    """Create a new API key (requires admin key)"""
    api_key = DB.create_key(name)
    return {"api_key": api_key, "name": name}

@router.get("/api-keys")
async def list_api_keys(
    _: str = Security(verify_admin_key)  # Requires admin key
):
    """List all API keys (requires admin key)"""
    return DB.list_keys()

@router.delete("/api-keys/{api_key}")
async def delete_api_key(
    api_key: str,
    _: str = Security(verify_admin_key)  # Requires admin key
):
    """Delete an API key (requires admin key)"""
    if not DB.delete_key(api_key):
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key deleted"}