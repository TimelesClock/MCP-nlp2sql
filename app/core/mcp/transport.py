from typing import Optional, Callable, Any, Dict
from mcp.transport import Transport, JSONRPCMessage
from app.utils.logging import logger

class MCPTransport(Transport):
    """Custom MCP transport implementation with enhanced logging and error handling"""
    
    def __init__(self):
        self.onmessage: Optional[Callable[[JSONRPCMessage], None]] = None # type: ignore
        self.onerror: Optional[Callable[[Exception], None]] = None
        self.onclose: Optional[Callable[[], None]] = None
        self._is_closed = False

    async def start(self):
        """Start the transport"""
        try:
            logger.info("Starting MCP transport")
            # Implementation specific to your transport needs
            pass
        except Exception as e:
            logger.error(f"Failed to start transport:")
            if self.onerror:
                self.onerror(e)
            raise

    async def send(self, message: JSONRPCMessage):
        """Send a message through the transport"""
        if self._is_closed:
            raise RuntimeError("Transport is closed")
            
        try:
            logger.debug(f"Sending message: {message}")
            # Implementation specific to your transport needs
            pass
        except Exception as e:
            logger.error(f"Failed to send message:")
            if self.onerror:
                self.onerror(e)
            raise

    async def close(self):
        """Close the transport"""
        if not self._is_closed:
            try:
                logger.info("Closing MCP transport")
                self._is_closed = True
                if self.onclose:
                    self.onclose()
            except Exception as e:
                logger.error(f"Error closing transport:")
                if self.onerror:
                    self.onerror(e)
                raise

    def _handle_message(self, raw_message: Dict[str, Any]):
        """Handle incoming messages"""
        try:
            if self.onmessage:
                self.onmessage(JSONRPCMessage(**raw_message))
        except Exception as e:
            logger.error(f"Error handling message:")
            if self.onerror:
                self.onerror(e)

class MCPStdioTransport(MCPTransport):
    """Stdio-specific transport implementation"""
    
    async def start(self):
        await super().start()
        # Add stdio-specific initialization
        
    async def send(self, message: JSONRPCMessage):
        await super().send(message)
        # Add stdio-specific sending logic
        
    async def close(self):
        await super().close()
        # Add stdio-specific cleanup

class MCPSSETransport(MCPTransport):
    """Server-Sent Events transport implementation"""
    
    def __init__(self, endpoint: str):
        super().__init__()
        self.endpoint = endpoint
        self.sse_client = None
        
    async def start(self):
        await super().start()
        # Add SSE-specific initialization
        
    async def send(self, message: JSONRPCMessage):
        await super().send(message)
        # Add SSE-specific sending logic
        
    async def close(self):
        await super().close()
        # Add SSE-specific cleanup