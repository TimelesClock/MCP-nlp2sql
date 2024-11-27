class MCPError(Exception):
    """Base exception for MCP-related errors"""
    pass

class SchemaError(MCPError):
    """Exception raised for schema-related errors"""
    pass

class QueryError(MCPError):
    """Exception raised for query-related errors"""
    pass

class SamplingError(MCPError):
    """Exception raised for sampling-related errors"""
    pass