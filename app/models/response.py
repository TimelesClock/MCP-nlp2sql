from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ErrorResponse(BaseModel):
    """Standard error response model"""
    code: int
    message: str
    details: Optional[Dict[str, Any]] = None

class ResourceContent(BaseModel):
    """Model for resource content"""
    uri: str
    mime_type: Optional[str] = None
    text: Optional[str] = None
    blob: Optional[str] = None

class ResourceResponse(BaseModel):
    """Model for resource response"""
    contents: List[ResourceContent]

class ToolResult(BaseModel):
    """Model for tool execution results"""
    content: List[Dict[str, Any]]
    is_error: bool = False
    error_message: Optional[str] = None

class SchemaResponse(BaseModel):
    """Model for database schema response"""
    tables: Dict[str, List[Dict[str, str]]]
    relationships: List[Dict[str, str]]
    metadata: Optional[Dict[str, Any]] = None

class SamplingResponse(BaseModel):
    """Model for sampling response"""
    model: str
    stop_reason: Optional[str] = None
    role: str = Field(..., regex='^(user|assistant)$')
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class CapabilitiesResponse(BaseModel):
    """Model for capabilities response"""
    prompts: Optional[List[Dict[str, Any]]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    resources: Optional[List[Dict[str, Any]]] = None
    schema: Optional[SchemaResponse] = None
    
class ProgressResponse(BaseModel):
    """Model for progress updates"""
    progress: float = Field(..., ge=0.0, le=1.0)
    total: float = Field(..., ge=0.0)
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None