#!/usr/bin/env python3

# dependencies = [
#   "mcp",
#   "aiomysql",
#   "python-dotenv",
#   "pydantic"
# ]

import os
import json
from typing import Optional, List, Dict, Any
import asyncio
from dotenv import load_dotenv
import aiomysql
from pydantic import BaseModel, Field
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Load environment variables
load_dotenv()

class QueryResult(BaseModel):
    columns: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    affected_rows: int = 0

class MySQLMCPServer:
    def __init__(self):
        self.server = Server("mysql-query-server")
        self.pool: Optional[aiomysql.Pool] = None
        self.setup_handlers()

    async def initialize_pool(self):
        """Initialize the MySQL connection pool"""
        if not self.pool:
            try:
                self.pool = await aiomysql.create_pool(
                    # host=os.getenv("MYSQL_HOST", "localhost"),
                    # port=int(os.getenv("MYSQL_PORT", "3306")),
                    # user=os.getenv("MYSQL_USER"),
                    # password=os.getenv("MYSQL_PASSWORD"),
                    # db=os.getenv("MYSQL_DATABASE"),
                    host="172.18.80.1",
                    port=3306,
                    user="root",
                    password="ZCh2kMRi_ALCBwRY",
                    db="t3-test",
                    autocommit=True,
                    pool_recycle=3600
                )
            except Exception as e:
                raise Exception(f"Failed to initialize MySQL pool: {str(e)}")

    def setup_handlers(self):
        """Set up all MCP handlers"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> list[types.Resource]:
            """Handle resources/list request"""
            if not self.pool:
                await self.initialize_pool()
                
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SHOW TABLES")
                    tables = [row[0] for row in await cursor.fetchall()]
                    
                    resources = []
                    for table in tables:
                        # Get table information
                        await cursor.execute(f"SHOW CREATE TABLE {table}")
                        create_info = await cursor.fetchone()
                        
                        resources.append(types.Resource(
                            uri=f"mysql://{table}",
                            name=table,
                            description=create_info[1] if create_info else f"MySQL table: {table}",
                            mime_type="application/json"
                        ))
                    return resources

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> list[types.TextContent]:
            """Handle resources/read request"""
            if not self.pool:
                await self.initialize_pool()
                
            table_name = uri.replace("mysql://", "")
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"DESCRIBE {table_name}")
                    structure = await cursor.fetchall()
                    
                    # Get some sample data
                    await cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                    sample_rows = await cursor.fetchall()
                    columns = [column[0] for column in cursor.description]
                    
                    response_data = {
                        "structure": [
                            {
                                "Field": row[0],
                                "Type": row[1],
                                "Null": row[2],
                                "Key": row[3],
                                "Default": row[4],
                                "Extra": row[5]
                            }
                            for row in structure
                        ],
                        "sample_data": [
                            dict(zip(columns, row))
                            for row in sample_rows
                        ]
                    }
                    
                    return [types.TextContent(
                        type="text",
                        text=json.dumps(response_data, indent=2, default=str)
                    )]
                    
        @self.server.list_prompts()
        async def handle_list_prompts() -> list[types.Prompt]:
            """Handle prompts/list request"""
            return [
                types.Prompt(
                    name="query_table",
                    description="Generate a query for a specific table",
                    arguments=[
                        types.PromptArgument(
                            name="table_name",
                            description="Name of the table to query",
                            required=True
                        ),
                        types.PromptArgument(
                            name="question",
                            description="Natural language question about the table",
                            required=True
                        )
                    ]
                )
            ]

        @self.server.get_prompt()
        async def handle_get_prompt(
            name: str,
            arguments: Optional[dict] = None
        ) -> types.GetPromptResult:
            """Handle prompts/get request"""
            if name != "query_table":
                raise ValueError(f"Unknown prompt: {name}")

            if not arguments or "table_name" not in arguments or "question" not in arguments:
                raise ValueError("Missing required arguments: table_name and question")

            # Get table structure for context
            if not self.pool:
                await self.initialize_pool()
                
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"DESCRIBE {arguments['table_name']}")
                    structure = await cursor.fetchall()
                    columns_info = [
                        f"- {row[0]} ({row[1]}): {row[2]}"
                        for row in structure
                    ]
                    
            table_context = f"""Table: {arguments['table_name']}
Columns:
{chr(10).join(columns_info)}"""

            return types.GetPromptResult(
                description=f"Generate a query for table {arguments['table_name']}",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=f"""Based on this table structure:

{table_context}

Generate a MySQL SELECT query for this question: {arguments['question']}

Respond in this JSON format:
{{
    "sql": "your SQL query here",
    "explanation": "explanation of what the query does"
}}"""
                        )
                    )
                ]
            )
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """Handle tools/list request"""
            return [
                {
                    "name": "query_database",
                    "description": "Execute a read-only SQL query against the MySQL database",
                    "arguments": {
                        "query": {
                            "description": "The SQL SELECT query to execute",
                            "required": True
                        }
                    }
                },
                {
                    "name": "list_tables",
                    "description": "List all available tables in the database",
                    "arguments": {}
                },
                {
                    "name": "describe_table",
                    "description": "Get the structure of a specific table",
                    "arguments": {
                        "table_name": {
                            "description": "Name of the table to describe",
                            "required": True
                        }
                    }
                }
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            """Handle tools/call request"""
            if not self.pool:
                await self.initialize_pool()
                
            if name == "query_database":
                result = await self.execute_query(arguments["query"])
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result.dict(), indent=2, default=str)
                )]
                
            elif name == "list_tables":
                tables = await self.list_tables()
                return [types.TextContent(
                    type="text",
                    text=json.dumps(tables, indent=2)
                )]
                
            elif name == "describe_table":
                structure = await self.describe_table(arguments["table_name"])
                return [types.TextContent(
                    type="text",
                    text=json.dumps(structure, indent=2)
                )]
                
            raise ValueError(f"Unknown tool: {name}")

    async def execute_query(self, query: str) -> QueryResult:
        """Execute a read-only SQL query"""
        # Basic SQL injection prevention
        if any(keyword.lower() in query.lower() 
               for keyword in ["insert", "update", "delete", "drop", "alter", "create"]):
            raise ValueError("Only SELECT queries are allowed")

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query)
                rows = await cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                return QueryResult(
                    columns=columns,
                    rows=[list(row) for row in rows],
                    affected_rows=cursor.rowcount
                )

    async def list_tables(self) -> list[str]:
        """List all tables in the database"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW TABLES")
                return [row[0] for row in await cursor.fetchall()]

    async def describe_table(self, table_name: str) -> list[dict]:
        """Get the structure of a specific table"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"DESCRIBE {table_name}")
                columns = ["Field", "Type", "Null", "Key", "Default", "Extra"]
                rows = await cursor.fetchall()
                return [
                    dict(zip(columns, row))
                    for row in rows
                ]

    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="mysql-query-server",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )

async def main():
    server = MySQLMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())