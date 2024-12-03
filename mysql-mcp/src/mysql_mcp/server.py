import asyncio
from typing import List, Dict, Any

import aiomysql
from pydantic import BaseModel, AnyUrl
from dotenv import load_dotenv

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Load environment variables
load_dotenv()

# Define data model for query results
class QueryResult(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    affected_rows: int = 0

# Initialize the server
server = Server("mysql-mcp")

# Global connection pool
pool: aiomysql.Pool | None = None

async def initialize_pool():
    """Initialize the MySQL connection pool if not already initialized"""
    global pool
    if not pool:
        try:
            pool = await aiomysql.create_pool(
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

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    List available MySQL tables as resources.
    Each table is exposed as a resource with a mysql:// URI scheme.
    """
    if not pool:
        await initialize_pool()
        
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SHOW TABLES")
            tables = [row[0] for row in await cursor.fetchall()]
            
            resources = []
            for table in tables:
                await cursor.execute(f"SHOW CREATE TABLE {table}")
                create_info = await cursor.fetchone()
                
                resources.append(types.Resource(
                    uri=AnyUrl(f"mysql://{table}"),
                    name=table,
                    description=create_info[1] if create_info else f"MySQL table: {table}",
                    mimeType="application/json"
                ))
            return resources

@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> list[types.TextContent]:
    """
    Read a specific table's structure and sample data by its URI.
    Returns table information and up to 5 sample rows.
    """
    if not pool:
        await initialize_pool()
        
    if uri.scheme != "mysql":
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

    table_name = uri.path.lstrip("/")
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Get table structure
            await cursor.execute(f"DESCRIBE {table_name}")
            structure = await cursor.fetchall()
            
            # Get sample data
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
                text=str(response_data)
            )]

@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """
    List available prompts.
    Each prompt can have optional arguments to customize its behavior.
    """
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

@server.get_prompt()
async def handle_get_prompt(
    name: str,
    arguments: Dict[str, str] | None = None
) -> types.GetPromptResult:
    """
    Generate a prompt by combining arguments with table structure.
    Returns a prompt that helps generate SQL queries based on natural language questions.
    """
    if name != "query_table":
        raise ValueError(f"Unknown prompt: {name}")

    if not arguments or "table_name" not in arguments or "question" not in arguments:
        raise ValueError("Missing required arguments: table_name and question")

    if not pool:
        await initialize_pool()
        
    async with pool.acquire() as conn:
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

Respond in this format:
{{
    "sql": "your SQL query here",
    "explanation": "explanation of what the query does"
}}"""
                )
            )
        ]
    )

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="query_database",
            description="Execute a read-only SQL query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL SELECT query to execute"
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="describe_table",
            description="Get the structure of a specific table",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to describe"
                    }
                },
                "required": ["table_name"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: Dict[str, Any] | None
) -> list[types.TextContent]:
    """
    Handle tool execution requests.
    Tools can query the database and return results.
    """
    if not pool:
        await initialize_pool()

    if not arguments:
        raise ValueError("Missing arguments")

    if name == "query_database":
        query = arguments.get("query")
        if not query:
            raise ValueError("Missing query argument")

        # Basic SQL injection prevention
        if any(keyword.lower() in query.lower() 
               for keyword in ["insert", "update", "delete", "drop", "alter", "create"]):
            raise ValueError("Only SELECT queries are allowed")

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query)
                rows = await cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                result = QueryResult(
                    columns=columns,
                    rows=[list(row) for row in rows],
                    affected_rows=cursor.rowcount
                )
                return [types.TextContent(
                    type="text",
                    text=str(result.dict())
                )]

    elif name == "describe_table":
        table_name = arguments.get("table_name")
        if not table_name:
            raise ValueError("Missing table_name argument")

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"DESCRIBE {table_name}")
                columns = ["Field", "Type", "Null", "Key", "Default", "Extra"]
                rows = await cursor.fetchall()
                structure = [dict(zip(columns, row)) for row in rows]
                return [types.TextContent(
                    type="text",
                    text=str(structure)
                )]

    raise ValueError(f"Unknown tool: {name}")

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mysql-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())