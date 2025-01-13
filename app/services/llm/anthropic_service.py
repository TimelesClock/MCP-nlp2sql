import asyncio
import json
from typing import Dict, Any, List
import anthropic
from app.config import Settings, settings
from app.core.mcp.session import MCPSession
from app.models.query import (
    RawLLMContent
)
from app.core.exceptions import SamplingError
from app.services.base.llm_service import BaseLLMService
from app.services.llm.base_tools import BaseLLMTools
from app.utils.logging import logger


class AnthropicService(BaseLLMService, BaseLLMTools):
    def __init__(self):
        super().__init__()
        self.client = anthropic.Anthropic(
            api_key=Settings.ANTHROPIC_API_KEY
        )

    def _convert_tools_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tools to Anthropic's format"""
        anthropic_tools = []
        
        for tool in tools:
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            }
            anthropic_tools.append(tool_def)
            
        return anthropic_tools

    async def process_chain(
        self,
        session: MCPSession,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        max_iterations: int = 5
    ) -> str:
        self.last_raw_response = []
        iteration = 0
        
        # Use all available tools
        all_tools = self._convert_tools_format(self.tools + tools)
        
        while iteration < max_iterations:
            logger.info(f"Processing message chain iteration {iteration}")
            response = await asyncio.to_thread(
                lambda: self.client.messages.create(
                    model=settings.ANTHROPIC_MODEL,
                    max_tokens=4096,
                    temperature=0,
                    messages=messages,
                    tools=all_tools
                )
            )
            
            tool_calls = []
            for content in response.content:
                if content.type == "tool_use":
                    if content.name in [t["name"] for t in self.tools]:
                        # Dashboard/Chart tool call
                        tool_calls.append({
                            "type": content.name,
                            "params": content.input
                        })
                        self.last_raw_response.append(
                            RawLLMContent(
                                type="tool_call",
                                text=json.dumps({
                                    "tool": content.name,
                                    "params": content.input
                                }),
                                id=content.id,
                                name=content.name,
                                input=content.input
                            )
                        )
                    else:
                        # MCP tool call
                        logger.info(f"Executing MCP tool: {content.name}")
                        tool_result = await session.call_tool(
                            content.name,
                            content.input
                        )
                        
                        messages.extend([
                            {"role": "assistant", "content": [{"type": "tool_use", "id": content.id, "name": content.name, "input": content.input}]},
                            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": content.id, "content": tool_result.content[0].text if tool_result.content else ""}]}
                        ])
                else:
                    self.last_raw_response.append(
                        RawLLMContent(
                            type=content.type,
                            text=getattr(content, 'text', None),
                            id=getattr(content, 'id', None),
                            name=getattr(content, 'name', None),
                            input=getattr(content, 'input', None)
                        )
                    )

            # If we had any tool calls, return the response
            if tool_calls:
                explanation = "\n".join(
                    content.text for content in response.content 
                    if content.type == "text"
                ) or "Executing operations..."
                
                return json.dumps({
                    "explanation": explanation,
                    "tool_calls": tool_calls
                })

            # If no tool calls, return text content
            text_response = "\n".join(
                content.text for content in response.content 
                if content.type == "text"
            )
            if text_response:
                return json.dumps({
                    "explanation": text_response,
                    "tool_calls": []
                })
                
            iteration += 1
            
        raise SamplingError("Exceeded maximum tool use iterations")