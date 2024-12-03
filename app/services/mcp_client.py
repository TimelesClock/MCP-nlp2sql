from typing import Optional, Dict, Any, List, Tuple
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import mcp.types as types
from app.config import settings
from app.core.mcp.session import MCPSession
from app.core.exceptions import MCPError
import shlex


class MCPClient:
    def __init__(self):
        # Set up the uv command to run the mysql-mcp server
        self.server_params = StdioServerParameters(
            command="uv",
            args=[
                "--directory",
                "/Users/leong/Documents/nlp2sql-api/mysql-mcp",
                "run",
                "mysql-mcp"
            ],
            env=None
        )
        
    async def create_session(self) -> MCPSession:
        """Create a new MCP session"""
        try:
            read, write = await stdio_client(self.server_params)
            session = ClientSession(read, write)
            return MCPSession(session)
        except Exception as e:
            raise MCPError(f"Failed to create MCP session: {str(e)}")

    async def with_session(self, callback):
        """Execute a callback with a managed MCP session"""
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                mcp_session = MCPSession(session)
                await mcp_session.initialize()
                return await callback(mcp_session)