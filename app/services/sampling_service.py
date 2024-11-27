import json
import asyncio
from typing import Optional, Dict, Any, List, Tuple
import anthropic
from app.config import settings
from app.models.query import ModelPreferences, SchemaAnalysis
from app.core.mcp.session import MCPSession
from app.core.exceptions import SamplingError
from app.utils.logging import logger
import re

class SamplingService:
    def __init__(self):
        self.claude = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY
        )

    async def generate_sql(
        self,
        session: MCPSession,
        question: str,
        schema: Dict[str, Any],
        model_preferences: Optional[ModelPreferences] = None
    ) -> Tuple[str, str, List[Dict[str, str]]]:
        """Generate SQL using Claude API"""
        try:
            system_prompt = f"""You are an expert in converting natural language questions into MySQL queries.

Database schema:
{json.dumps(schema, indent=2)}

Generate a MySQL query to answer this question. Return ONLY valid JSON in this format:
{{
    "sql": "your SQL query here",
    "explanation": "detailed explanation of what the query does",
    "thought_process": [
        {{"step": "Understanding the request", "thought": "explanation"}},
        {{"step": "Analyzing schema", "thought": "explanation"}},
        {{"step": "Formulating query", "thought": "explanation"}}
    ]
}}

Important:
1. Only use SELECT queries
2. Handle NULL values appropriately
3. Use proper table/column prefixes to avoid ambiguity
4. Include proper JOIN conditions
5. Add appropriate WHERE clauses
6. Format dates correctly using MySQL date functions"""

            response = await asyncio.to_thread(
                lambda: self.claude.messages.create(
                    model=settings.ANTHROPIC_MODEL,
                    max_tokens=2000,
                    temperature=0,
                    system=system_prompt,
                    messages=[{"role": "user", "content": question}]
                )
            )
            
            logger.debug(f"Claude response: {response.content}")
            result = self._parse_claude_response(response.content[0].text)
            
            return (
                result["sql"],
                result["explanation"],
                result["thought_process"]
            )
            
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}", exc_info=True)
            raise SamplingError(f"Failed to generate SQL: {str(e)}")

    async def refine_sql(
        self,
        session: MCPSession,
        original_sql: str,
        error_msg: str,
        schema: Dict[str, Any]
    ) -> Tuple[str, str, List[Dict[str, str]]]:
        """Refine SQL query based on error message"""
        try:
            system_prompt = f"""You are an expert in SQL query debugging and optimization.

Original SQL query that failed:
{original_sql}

Error message:
{error_msg}

Database schema:
{json.dumps(schema, indent=2)}

Fix the SQL query to resolve the error. Return ONLY valid JSON in this format:
{{
    "sql": "fixed SQL query",
    "explanation": "detailed explanation of fixes made",
    "thought_process": [
        {{"step": "Error Analysis", "thought": "explanation of what caused the error"}},
        {{"step": "Query Review", "thought": "analysis of the original query"}},
        {{"step": "Fix Implementation", "thought": "explanation of how the error was fixed"}}
    ]
}}

Important fixes to consider:
1. Add table aliases to resolve ambiguous column references
2. Verify all column names exist in their respective tables
3. Ensure proper JOIN conditions
4. Use correct MySQL date/time functions
5. Handle NULL values appropriately
6. Keep the original query's intent and functionality"""

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
            
            # Validate the refined SQL has basic requirements
            if not result["sql"].strip().lower().startswith("select"):
                raise SamplingError("Refined query must be a SELECT statement")
            
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
            # Clean response text
            response_text = response_text.strip()
            json_match = re.search(r'({[\s\S]*})', response_text)
            
            if not json_match:
                raise SamplingError("No JSON found in response")
            
            # Clean the matched JSON text
            cleaned_text = json_match.group(1)
            cleaned_text = ''.join(
                char for char in cleaned_text 
                if ord(char) >= 32 and ord(char) < 127
            )
            
            logger.debug(f"Cleaned response text: {cleaned_text}")
            
            try:
                result = json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                logger.error(f"Attempted to parse: {cleaned_text}")
                raise SamplingError(f"Failed to parse Claude response as JSON: {str(e)}")

            # Validate required fields
            required_fields = ["sql", "explanation", "thought_process"]
            missing_fields = [field for field in required_fields if field not in result]
            if missing_fields:
                raise SamplingError(f"Missing required fields in response: {', '.join(missing_fields)}")

            return result
            
        except Exception as e:
            logger.error(f"Error parsing Claude response: {str(e)}", exc_info=True)
            logger.error(f"Raw response: {response_text}")
            raise SamplingError(f"Failed to parse Claude response: {str(e)}")