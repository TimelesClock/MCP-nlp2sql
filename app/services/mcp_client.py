# app/services/mcp_client.py

import os
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Any, AsyncContextManager
from contextlib import asynccontextmanager
from app.utils.logging import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.core.mcp.session import MCPSession
from app.core.exceptions import MCPError


@dataclass
class ServerConfig:
    """Configuration for an MCP server"""
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None


from app.config import settings
from typing import Dict, Optional

class MCPServerManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.servers: Dict[str, ServerConfig] = {}
        self.load_config()
    
    def _get_server_env(self, server_name: str) -> Optional[Dict[str, str]]:
        """Get environment variables for a server from settings"""
        env_var_name = f"MCP_{server_name.upper()}_ENV"
        base_env_vars = getattr(settings, env_var_name, {})
        
        # Create new dict with resolved environment variables
        env = {}
        for key in base_env_vars.keys():
            # For the MCP server, we need to pass the actual values, not the prefixed env vars
            env[key] = os.environ.get(f"{env_var_name}__{key}", base_env_vars[key])
        
        # Add system PATH and other standard env vars
        if 'PATH' not in env:
            env['PATH'] = os.environ.get('PATH', '')
            
        # Add additional paths on Unix systems
        if os.name != 'nt':
            additional_paths = [
                '/usr/local/bin',
                '/usr/bin',
                '/bin',
                os.path.expanduser('~/.local/bin'),
                os.path.expanduser('~/.cargo/bin')
            ]
            env['PATH'] = os.pathsep.join([env['PATH']] + additional_paths)
        return env
    
    def get_server_config(self, server_name: str) -> ServerConfig:
        """Get configuration for a specific server"""
        if server_name not in self.servers:
            raise MCPError(f"Server '{server_name}' not found in configuration")
        return self.servers[server_name]

    def load_config(self):
        """Load server configurations from JSON file"""
        if not os.path.exists(self.config_path):
            return

        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            server_configs = config.get('mcpServers', {})
            
            for server_name, server_config in server_configs.items():
                self.servers[server_name] = ServerConfig(
                    command=server_config['command'],
                    args=server_config.get('args', []),
                    env=self._get_server_env(server_name)
                )
        except Exception as e:
            raise MCPError(f"Failed to load MCP config from {self.config_path}: {str(e)}")
    def list_servers(self) -> List[str]:
        """Get list of configured server names"""
        return list(self.servers.keys())


class BaseMCPClient:
    """Base client for managing MCP server connections"""
    def __init__(self, config_path: str):
        self.server_manager = MCPServerManager(config_path)

    def create_server_params(self, server_name: str) -> StdioServerParameters:
        """Create server parameters for a given server configuration"""
        config = self.server_manager.get_server_config(server_name)
        return StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env
        )

    @asynccontextmanager
    async def create_session(self, server_name: str) -> AsyncContextManager[MCPSession]: # type: ignore
        """Create a new MCP session for a specific server"""
        server_params = self.create_server_params(server_name)
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    mcp_session = MCPSession(session)
                    await mcp_session.initialize()
                    yield mcp_session
        except Exception as e:
            # Add more detailed error information
            error_msg = f"Failed to create MCP session for '{server_name}': {str(e)}"
            if "No such file or directory" in str(e):
                error_msg += f"\nCommand '{server_params.command}' not found in PATH: {server_params.env.get('PATH')}"
            raise MCPError(error_msg)

    async def with_session(self, server_name: str, callback: Callable[[MCPSession], Any]):
        """Execute a callback with a managed MCP session"""
        async with self.create_session(server_name) as session:
            return await callback(session)

    async def with_sessions(self, server_names: List[str], callback: Callable[[Dict[str, MCPSession]], Any]):
        """Execute a callback with multiple managed MCP sessions"""
        sessions = {}
        try:
            for server_name in server_names:
                async with self.create_session(server_name) as session:
                    sessions[server_name] = session
            return await callback(sessions)
        except Exception as e:
            raise MCPError(f"Failed to create sessions: {str(e)}")