from typing import Any, List, Dict, Optional
from mcp import ClientSession
from app.core.exceptions import MCPError
import mcp.types as types

class MCPSession:
    """Wrapper around MCP ClientSession with additional functionality"""
    
    def __init__(self, session: ClientSession):
        self.session = session
        self.initialized = False

    async def initialize(self):
        """Initialize the MCP session"""
        if not self.initialized:
            try:
                await self.session.initialize()
                self.initialized = True
            except Exception as e:
                raise MCPError(f"Failed to initialize MCP session:  ")

    async def list_resources(self) -> List[types.Resource]:
        """List available resources"""
        await self._ensure_initialized()
        return await self.session.list_resources()

    async def read_resource(self, uri: str) -> List[types.ResourceContents]:
        """Read a resource by URI"""
        await self._ensure_initialized()
        return await self.session.read_resource(uri)

    async def list_prompts(self) -> List[types.Prompt]:
        """List available prompts"""
        await self._ensure_initialized()
        return await self.session.list_prompts()

    async def get_prompt(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> types.GetPromptResult:
        """Get a specific prompt"""
        await self._ensure_initialized()
        return await self.session.get_prompt(name, arguments)

    async def list_tools(self) -> List[types.Tool]:
        """List available tools"""
        await self._ensure_initialized()
        return await self.session.list_tools()

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> List[types.TextContent]:
        """Call a specific tool"""
        await self._ensure_initialized()
        return await self.session.call_tool(name, arguments)

    async def create_message(
        self,
        messages: List[Dict[str, Any]],
        model_preferences: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        include_context: Optional[str] = None
    ) -> types.CreateMessageResult:
        """Create a message using sampling"""
        await self._ensure_initialized()
        return await self.session.create_message(
            messages=messages,
            model_preferences=model_preferences,
            max_tokens=max_tokens,
            temperature=temperature,
            include_context=include_context
        )

    async def _ensure_initialized(self):
        """Ensure session is initialized"""
        if not self.initialized:
            raise MCPError("MCP session not initialized")