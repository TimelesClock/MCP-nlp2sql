import json
import asyncio
from typing import Dict, Any, List
import openai
from app.config import settings
from app.core.mcp.session import MCPSession
from app.models.query import (
    RawLLMContent
)
from app.core.exceptions import SamplingError
from app.services.base.llm_service import BaseLLMService
from app.services.llm.base_tools import BaseLLMTools
from app.utils.logging import logger

class OpenAIService(BaseLLMService, BaseLLMTools):
    def __init__(self):
        super().__init__()
        self.client = openai.OpenAI(
            api_key=settings.OPENAI_API_KEY
        )

    def _convert_tools_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tools to OpenAI's function calling format"""
        openai_tools = []
        
        for tool in tools:
            function = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            }
            openai_tools.append(function)
            
        return openai_tools

    async def process_chain(
        self,
        session: MCPSession,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        max_iterations: int = 10
    ) -> str:
        self.last_raw_response = []
        iteration = 0
        
        formatted_messages = []
        for msg in messages:
            formatted_msg = {
                "role": msg["role"],
                "content": msg["content"]
            }
            if "tool_calls" in msg:
                formatted_msg["tool_calls"] = msg["tool_calls"]
            if "tool_call_id" in msg:
                formatted_msg["tool_call_id"] = msg["tool_call_id"]
            formatted_messages.append(formatted_msg)

        # Use all available tools
        all_tools = self.tools + tools
        
        while iteration < max_iterations:
            logger.info(f"Processing message chain iteration {iteration}")
            logger.info(f"Latest messages: {formatted_messages[-1]}")
            openai_tools = self._convert_tools_format(all_tools)
            try:
                logger.info("Calling OpenAI API")
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=settings.OPENAI_MODEL,
                    messages=formatted_messages,
                    tools=openai_tools,
                    tool_choice="auto",
                    temperature=0
                )
                logger.info(f"OpenAI API response: {response}")
                
                message = response.choices[0].message

                # Handle tool calls
                if message.tool_calls:
                    tool_calls = []
                    
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        if tool_name in [t["name"] for t in self.tools]:
                            # Dashboard/Chart tool call
                            tool_calls.append({
                                "type": tool_name,
                                "params": tool_args
                            })
                            self.last_raw_response.append(
                                RawLLMContent(
                                    type="tool_call",
                                    text=json.dumps({
                                        "tool": tool_name,
                                        "params": tool_args
                                    }),
                                    id=tool_call.id,
                                    name=tool_name,
                                    input=tool_args
                                )
                            )
                        else:
                            # MCP tool call
                            tool_result = await session.call_tool(tool_name, tool_args)
                            formatted_messages.extend([
                                {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [{
                                        "id": tool_call.id,
                                        "type": "function",
                                        "function": {
                                            "name": tool_name,
                                            "arguments": json.dumps(tool_args)
                                        }
                                    }]
                                },
                                {
                                    "role": "tool",
                                    "content": tool_result.content[0].text if tool_result.content else "",
                                    "tool_call_id": tool_call.id
                                }
                            ])

                    if tool_calls:
                        return json.dumps({
                            "explanation": message.content or "Executing operations...",
                            "tool_calls": tool_calls
                        })

                else:
                    self.last_raw_response = [
                        RawLLMContent(
                            type="text",
                            text=message.content,
                            id=None,
                            name=None,
                            input=None
                        )
                    ]
                    return json.dumps({
                        "explanation": message.content,
                        "tool_calls": []
                    })

            except Exception as e:
                logger.error(f"Error in OpenAI API call: {str(e)}")
                raise SamplingError(f"OpenAI API call failed: {str(e)}")
                
            iteration += 1
            
        raise SamplingError("Exceeded maximum tool use iterations")

