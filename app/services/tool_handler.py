from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import xml.etree.ElementTree as ET
import json
from datetime import datetime
from uuid import uuid4

class ToolCallLog(BaseModel):
    type: str
    status: str
    timestamp: datetime
    logs: List[str]
    result: Dict[str, Any]
    id: Optional[str] = None

    @classmethod
    def from_xml_string(cls, xml_string: str) -> List['ToolCallLog']:
        """Parse tool calls from XML string format"""
        tool_calls = []
        try:
            root = ET.fromstring(xml_string)
            for tool_call in root.findall('.//tool_call'):
                # Extract base attributes
                call_type = tool_call.get('type')
                status = tool_call.get('status')
                timestamp = tool_call.get('timestamp')
                
                # Parse logs
                logs_elem = tool_call.find('logs')
                logs = json.loads(logs_elem.text) if logs_elem is not None else []
                
                # Parse result
                result_elem = tool_call.find('result')
                result = json.loads(result_elem.text) if result_elem is not None else {}
                
                tool_calls.append(cls(
                    type=call_type,
                    status=status,
                    timestamp=datetime.fromisoformat(timestamp.replace('Z', '+00:00')),
                    logs=logs,
                    result=result,
                    id=str(uuid4())
                ))
        except Exception as e:
            raise ValueError(f"Failed to parse tool call XML: {str(e)}")
            
        return tool_calls

    def to_assistant_message(self) -> Dict[str, Any]:
        """Convert tool call to assistant message format with tool_calls"""
        return {
            "role": "assistant",
            "content": "",  # Content is empty for messages with tool calls
            "tool_calls": [{
                "id": self.id,
                "type": "function",  # OpenAI expects "function" type
                "function": {
                    "name": self.type,
                    "arguments": json.dumps({
                        "params": self.result.get("result", {})
                    })
                }
            }]
        }

    def to_tool_message(self) -> Dict[str, Any]:
        """Convert tool call to tool message format"""
        return {
            "role": "tool",
            "content": json.dumps({
                "status": self.status,
                "logs": self.logs,
                "result": self.result
            }, indent=2),
            "tool_call_id": self.id
        }

class MessageWithToolHistory(BaseModel):
    """Extended Message model that includes tool call history"""
    content: str
    role: str
    tool_calls: Optional[str] = None
    raw_llm_response: Optional[List[Dict[str, Any]]] = None
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages including tool calls if present"""
        messages = []
        
        # Add the base message with content
        if self.raw_llm_response:
            # Use raw LLM response if available
            json_responses = [
                r.get("text") for r in self.raw_llm_response 
                if r.get("type") == "text" and r.get("text")
            ]
            if json_responses:
                content = json_responses[-1]
            else:
                content = self.content
        else:
            content = self.content

        messages.append({
            "role": self.role,
            "content": content
        })
        
        # Add tool calls if present
        if self.tool_calls:
            try:
                tool_calls = ToolCallLog.from_xml_string(self.tool_calls)
                for call in tool_calls:
                    # Add assistant message with tool_calls
                    messages.append(call.to_assistant_message())
                    # Add tool response message
                    messages.append(call.to_tool_message())
            except ValueError as e:
                raise ValueError(f"Invalid tool calls format: {str(e)}")
                
        return messages