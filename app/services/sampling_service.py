import json
import asyncio
from typing import Optional, Dict, Any, List, Tuple
import anthropic
from app.config import settings
from app.models.query import ModelPreferences
from app.core.mcp.session import MCPSession
from app.core.exceptions import SamplingError
from app.utils.logging import logger
import re

class SamplingService:
    def __init__(self):
        self.claude = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY
        )

    async def generate_sql_and_viz(
        self,
        session: MCPSession,
        question: str,
        schema: Dict[str, Any],
        model_preferences: Optional[ModelPreferences] = None
    ) -> Tuple[str, str, List[Dict[str, str]], Dict[str, Any]]:
        """Generate SQL and Metabase question settings using Claude API"""
        try:
            system_prompt = f"""You are an expert in converting natural language questions into SQL queries and Metabase visualizations.

Database schema:
{json.dumps(schema, indent=2)}

Generate a MySQL query and Metabase question settings to answer this question.
Consider the type of data and what visualization would best represent it.

Return ONLY valid JSON in this format:
{{
    "sql": "your SQL query here using escape characters when needed",
    "explanation": "detailed explanation of what the query does",
    "thought_process": [
        {{"step": "Understanding the request", "thought": "explanation"}},
        {{"step": "Analyzing schema", "thought": "explanation"}},
        {{"step": "Choosing visualization", "thought": "explanation"}}
    ],
    "metabase_question": {{
        "name": "clear name for the question",
        "description": "detailed description",
        "type": "question",
        "dataset": false,
        "dataset_query": {{
            "type": "native",
            "native": {{
                "query": "your SQL query here with newlines and indentation and spaces using escape characters and explanation using comments",
                "template-tags": {{}}
            }},
            "database": 270009
        }},
        "display": "type of visualization",
        "displayIsLocked":true,
        "visualization_settings": {{
            "graph.dimensions": ["columns for x-axis"],
            "graph.metrics": ["columns for y-axis"],
            "graph.show_values": true,
            "stackable.stack_type": "stacked/normalized/null",
        }},
        "parameters": [],
        "parameter_mappings": [],
        "result_metadata": [
            {{
                "name": "column name",
                "display_name": "display name",
                "base_type": "type/Text or type/Integer or type/Float or type/DateTime",
                "semantic_type": null,
                "field_ref": ["field", "column_name", {{"base-type": "type/Text"}}]
            }}
        ]
    }}
}}

Important:
1. Choose appropriate visualization type:
   - Time series → line, area, bar
   - Comparisons → bar, pie
   - Distributions → scatter
   - Geographic → map
   The available visualization types are: line, bar, combo, area, row, waterfall, scatter, pie, funnel, trend, progress, gauge, number, table, pivot table, map
2. Include all necessary column metadata
3. Use proper data types
4. Set meaningful display names
5. Ensure that it is in valid JSON format
6. Ensure that when the user requests for grouped and time series, the x or y axis dimension might need multiple series breakouts
7. Ensure that when using stacked visualizations, the dimensions are set correctly
8. Stacked bar charts are preferred over multi line charts for daily/weekly aggregates
9. Try to sort the data in a meaningful way
10. Ensure that the new lines and indentations are using escape characters (\\n, \\t)
11. Ensure that strings are not using python's triple quotes (\"\"\")
"""

            logger.debug(f"Sending generation request to Claude")
            
            response = await asyncio.to_thread(
                lambda: self.claude.messages.create(
                    model=settings.ANTHROPIC_MODEL,
                    max_tokens=4096,
                    temperature=0,
                    system=system_prompt,
                    messages=[{"role": "user", "content": question}]
                )
            )
            
            logger.debug(f"Claude response: {response.content}")
            result = self._parse_claude_response(response.content[0].text)
            
            # Extract required components
            sql_query = result["sql"]
            explanation = result["explanation"]
            thought_process = result["thought_process"]
            metabase_question = result["metabase_question"]
            
            # Ensure required fields exist
            self._validate_metabase_question(metabase_question)
            
            return (
                sql_query,
                explanation,
                thought_process,
                metabase_question
            )
            
        except Exception as e:
            logger.error(f"Error generating SQL and visualization: {str(e)}", exc_info=True)
            raise SamplingError(f"Failed to generate SQL and visualization: {str(e)}")

    def _validate_metabase_question(self, question: Dict[str, Any]) -> None:
        """Validate Metabase question format"""
        required_fields = {
            "name": str,
            "type": str,
            "dataset_query": dict,
            "display": str,
            "visualization_settings": dict,
            "parameters": list,
            "parameter_mappings": list
        }
        
        for field, field_type in required_fields.items():
            if field not in question:
                raise SamplingError(f"Missing required field: {field}")
            if not isinstance(question[field], field_type):
                raise SamplingError(f"Invalid type for field {field}")
                
        # Validate dataset_query structure
        query = question["dataset_query"]
        if "type" not in query or query["type"] != "native":
            raise SamplingError("Invalid dataset_query type")
            
        if "native" not in query or "query" not in query["native"]:
            raise SamplingError("Invalid native query structure")
            
        # Validate display type
        valid_displays = ["line", "bar", "pie", "scatter", "area", "table", "map"]
        if question["display"] not in valid_displays:
            raise SamplingError(f"Invalid display type: {question['display']}")

    async def refine_sql(
        self,
        session: MCPSession,
        original_sql: str,
        error_msg: str,
        schema: Dict[str, Any]
    ) -> Tuple[str, str, List[Dict[str, str]]]:
        """Refine SQL query based on error message"""
        system_prompt = f"""You are an expert in SQL query debugging.

Original SQL query that failed:
{original_sql}

Error message:
{error_msg}

Database schema:
{json.dumps(schema, indent=2)}

Fix the SQL query. Return ONLY valid JSON in this format:
{{
    "sql": "fixed SQL query",
    "explanation": "explanation of fixes",
    "thought_process": [
        {{"step": "Error Analysis", "thought": "what caused the error"}},
        {{"step": "Fix Implementation", "thought": "how the error was fixed"}}
    ]
}}"""

        try:
            logger.info(f"Sending refinement request to Claude for error: {error_msg}")
            
            response = await asyncio.to_thread(
                lambda: self.claude.messages.create(
                    model=settings.ANTHROPIC_MODEL,
                    max_tokens=2000,
                    temperature=0,
                    system=system_prompt,
                    messages=[{
                        "role": "user",
                        "content": "Please fix this SQL query"
                    }]
                )
            )

            logger.debug(f"Claude refinement response: {response.content}")
            result = self._parse_claude_response(response.content[0].text)
            
            return (
                result["sql"],
                result["explanation"],
                result["thought_process"]
            )
            
        except Exception as e:
            logger.error(f"Error refining SQL: {str(e)}", exc_info=True)
            logger.error(f"Original query: {original_sql}")
            logger.error(f"Error message: {error_msg}")
            raise SamplingError(f"Failed to refine SQL: {str(e)}")

    def _parse_claude_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate Claude's response"""
        try:
            response_text = response_text.strip()
            json_match = re.search(r'({[\s\S]*})', response_text)
            
            if not json_match:
                raise SamplingError("No JSON found in response")
            
            cleaned_text = json_match.group(1)
            cleaned_text = ''.join(
                char for char in cleaned_text 
                if ord(char) >= 32 and ord(char) < 127
            )
            
            try:
                result = json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                logger.error(f"Attempted to parse: {cleaned_text}")
                raise SamplingError(f"Failed to parse Claude response as JSON: {str(e)}")

            return result
            
        except Exception as e:
            logger.error(f"Error parsing Claude response: {str(e)}", exc_info=True)
            logger.error(f"Raw response: {response_text}")
            raise SamplingError(f"Failed to parse Claude response: {str(e)}")