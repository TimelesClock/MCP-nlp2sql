#!/bin/bash

# Make sure we're in the project root
cd "$(dirname "$0")"

# Create necessary directories if they don't exist
mkdir -p app/services/mcp

# Move MySQL MCP server to correct location
mv mysql_mcp_server.py app/services/mcp/

# Set proper permissions
chmod +x app/services/mcp/mysql_mcp_server.py

# Update config to point to correct location
sed -i 's|./mysql_mcp_server.py|app/services/mcp/mysql_mcp_server.py|g' .env

echo "Project initialized successfully!"