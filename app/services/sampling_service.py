import json
import re
from typing import Optional, Dict, Any, List, Tuple
from app.core.mcp.session import MCPSession
from app.models.query import (
    Message, QueryResponse, ModelPreferences, ToolCall, 
    QueryType, RawLLMContent
)
from app.core.exceptions import SamplingError
from app.services.llm.anthropic_service import AnthropicService
from app.services.llm.openai_service import OpenAIService
from app.services.tool_handler import MessageWithToolHistory
from app.utils.logging import logger

class SamplingService:
    def __init__(self, api_provider: str = "anthropic"):
        """Initialize the sampling service with specified API provider"""
        if api_provider == "anthropic":
            self.llm_service = AnthropicService()
        elif api_provider == "openai":
            self.llm_service = OpenAIService()
        else:
            raise ValueError(f"Unsupported API provider: {api_provider}")

    async def refine_sql(
        self,
        session: MCPSession,
        original_sql: str,
        error_message: str,
        schema: Dict[str, Any]
    ) -> Tuple[str, str, List[Dict[str, str]]]:
        """Refine SQL query based on error message"""
        try:
            system_prompt = f"""You are an expert SQL debugger. Fix this MySQL query based on the error message.

Schema:
<schema>
{json.dumps(schema, indent=2)}
</schema>

Original query:
{original_sql}

Error:
{error_message}

Return ONLY valid JSON in this format:
{{
    "sql": "Fixed SQL query",
    "explanation": "Explanation of what was wrong and how it was fixed",
    "thought_process": [
        {{"step": "Error analysis", "thought": "explanation"}},
        {{"step": "Schema validation", "thought": "explanation"}},
        {{"step": "Query correction", "thought": "explanation"}}
    ]
}}"""

            final_text = await self.llm_service.process_chain(
                session=session,
                messages=[{"role": "user", "content": system_prompt}],
                tools=[]
            )

            if not final_text:
                raise SamplingError("No text response received from LLM during refinement")

            json_match = re.search(r'({[\s\S]*})', final_text)
            if not json_match:
                raise SamplingError("No valid JSON response found in LLM refinement output")

            response = json.loads(json_match.group(1))
            
            return (
                response["sql"],
                response["explanation"],
                response["thought_process"]
            )

        except Exception as e:
            logger.error(f"Error refining SQL: {str(e)}")
            raise SamplingError(f"Failed to refine SQL: {str(e)}")

    async def process_query(
        self,
        session: MCPSession,
        question: str,
        database_name: str,
        schema: Dict[str, Any],
        model_preferences: Optional[ModelPreferences] = None,
        message_history: Optional[List[Message]] = None,
        type: Optional[QueryType] = "chart",
        chart_id: Optional[int] = None
    ) -> QueryResponse:
        """Process a natural language query using tool-based approach"""
        try:
            # Construct the system prompt based on query type
            system_prompt = self._construct_system_prompt(
                type=type,
                database_name=database_name,
                schema=schema,
                chart_id=chart_id
            )

            # Format messages for the LLM
            messages = self._format_messages(
                system_prompt=system_prompt,
                question=question,
                message_history=message_history
            )

            # Get MCP tools if needed
            mcp_tools = await session.list_tools() if type == "chart" else []
            tools = self._extract_tools(mcp_tools)

            # Process with LLM
            response = await self.llm_service.process_chain(
                session=session,
                messages=messages,
                tools=tools
            )

            # Parse response
            parsed_response = self._parse_llm_response(response)

            return QueryResponse(
                explanation=parsed_response["explanation"],
                tool_calls=[ToolCall(**call) for call in parsed_response["tool_calls"]],
                raw_llm_response=self.llm_service.last_raw_response
            )

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            raise SamplingError(f"Failed to process query: {str(e)}")

    def _construct_system_prompt(
        self,
        type: QueryType,
        database_name: str,
        schema: Dict[str, Any],
        chart_id: Optional[int] = None
    ) -> str:
        """Construct appropriate system prompt based on query type"""
        base_prompt = f"""Database schema:
{json.dumps(schema, indent=2)}

Working with database: {database_name}

Ignore the database data for now as it has mock data.
"""
        if type == "chart":
            # User is in Metabase question editor
            base_prompt += """You are an expert in SQL and data visualization for Metabase. Help create an effective visualization for the user's question.
            
Bacgkround: The user is on a Metabase question page, trying to create a visualization to answer a specific question. They need help with writing the SQL query and configuring the visualization settings.

Your task:
1. Understand the user's query requirements
2. Write an appropriate SQL query to fetch the required data
3. Choose the best visualization type to represent this data
4. Configure visualization settings for clear data presentation
5. Call preview_chart to generate a visualization

Disabled tools: create_chart, rearrange_dashboard, add_markdown

Important: Always respond with a tool_use

Generate a preview visualization using the preview_chart tool with:
- Clear and efficient SQL query
- Appropriate visualization type (line, bar, pie, etc.)
- Well-configured visualization settings
- Meaningful axis labels and formatting
- Clear title and description

Important Visualization Guidelines:
1. Time Series Data:
- Use "line" for continuous trends
- Use "bar" for discrete time periods
- Set x_axis.scale to "timeseries" ONLY for date/datetime columns
- Consider "rotate-45" for dense time labels
- Format date/time columns appropriately

2. Comparisons:
- Use "bar" for comparing categories
- Use "pie" for part-to-whole (max 8 segments)
- Set show_values: true for important numbers
- Use stackable.stack_type: "normalized" for percentages
- Format percentage columns with appropriate scale

3. Distributions:
- Use "scatter" for correlations
- Set appropriate axis scales (log/linear)
- Enable trendline if pattern is important
- Format numeric columns with scientific notation if needed

4. Multiple Series:
- Use stackable.stack_type: "stacked" for cumulative values
- Use "bar" for time series comparisons
- Set clear dimension and metric names
- Format each series appropriately

Number Formatting:
- Use "decimal" for whole numbers
- Use "percent" for percentages (scale: 0.01)
- Use "scientific" for large numbers
- Use "currency" for monetary values
- Add number_separators for readability

Available visualization types: line, bar, combo, area, row, waterfall, scatter, pie, funnel, trend, progress, gauge, number, table, pivot table, map"""

        else:  # dashboard
            # User is on dashboard page
            base_prompt += """You are an expert in dashboard design and organization for Metabase. Help create and organize an effective dashboard layout.
Background: The user is on a Metabase dashboard page, trying to create a dashboard to visualize multiple questions and metrics. They need help with organizing the visualizations and adding context to the dashboard.

If the user requests for a task that requires multiple steps, add the require_followup parameter to the tool call

Your task:
1. Understand the user's dashboard requirements
2. Create appropriate visualizations using create_chart
3. Organize content with rearrange_dashboard
4. Add context with add_markdown where helpful

If vizualisation_settings has a text field, it is a text card, and delete_chard should not be called for it

Disabled tools: preview_chart

Best Practices:
- Group related visualizations together
- Use consistent formatting across charts
- Add explanatory text for context
- Consider progressive disclosure (most important first)
- Maintain clean, uncluttered layout"""
        return base_prompt

    def _format_messages(
        self,
        system_prompt: str,
        question: str,
        message_history: Optional[List[MessageWithToolHistory]] = None
    ) -> List[Dict[str, str]]:
        """Format messages for LLM processing including tool history"""
        messages = [{"role": "developer", "content": system_prompt}]
        
        if message_history:
            for msg in message_history:
                try:
                    # Get all messages including tool calls
                    msg_list = msg.get_messages()
                    messages.extend(msg_list)
                except ValueError as e:
                    logger.warning(f"Failed to process message history: {str(e)}")
                    # Fallback to basic message without tool calls
                    messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })

        messages.append({"role": "user", "content": question})
        return messages

    def _extract_tools(self, mcp_tools: List[Any]) -> List[Dict[str, Any]]:
        """Extract tools from MCP response"""
        tools = []
        
        # MCP returns tools in a specific format: [("tools", [tool1, tool2, ...])]
        tools_tuple = next(
            (item for item in mcp_tools if isinstance(item, tuple) and 
                len(item) == 2 and item[0] == "tools"),
            None
        )
        
        if tools_tuple and isinstance(tools_tuple[1], list):
            tools_list = tools_tuple[1]
            for tool in tools_list:
                try:
                    # MCP tools contain name, description, and inputSchema
                    if hasattr(tool, 'name') and hasattr(tool, 'description') and hasattr(tool, 'inputSchema'):
                        tool_def = {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema
                        }
                        tools.append(tool_def)
                    else:
                        logger.warning(f"Incomplete tool definition: {tool}")
                except Exception as e:
                    logger.error(f"Error converting MCP tool {tool}: {str(e)}")
                    continue
                    
        return tools

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured format"""
        try:
            logger.info(f"LLM response: {response}")
            return json.loads(response,strict=False)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            raise SamplingError("Failed to parse LLM response")