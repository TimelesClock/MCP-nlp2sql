import base64
import json
from typing import Optional, Dict, Any, List, Union, Literal
from typing_extensions import Annotated
from pydantic import BaseModel, Field, ConfigDict, model_validator
from enum import Enum
from datetime import datetime
from app.services.tool_handler import MessageWithToolHistory
from app.utils.logging import logger

class ToolType(str, Enum):
    LOAD_CHART = "load_chart"
    CREATE_CHART = "create_chart"
    UPDATE_CHART = "update_chart"
    DELETE_CHART = "delete_chart"
    REARRANGE_DASHBOARD = "rearrange_dashboard"
    ADD_MARKDOWN = "add_markdown"
    PREVIEW_CHART = "preview_chart"
    LIST_CHARTS = "list_charts"
    REQUIRES_FOLLOWUP = "requires_followup"
    GET_DASHBOARD_CARDS = "get_dashboard_cards"

class ToolCall(BaseModel):
    """Model for tool calls made by LLM"""
    type: ToolType
    params: Dict[str, Any]


class ToolResponse(BaseModel):
    """Response from tool execution"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SeriesSettings(BaseModel):
    title: Optional[str] = None
    color: Optional[str] = None
    show_values: Optional[bool] = None

class SeriesOrderSetting(BaseModel):
    name: str
    enabled: bool

class SmartScalarComparison(BaseModel):
    type: str
    value: Any

class PieRow(BaseModel):
    name: str
    value: Any

YAxisScale = Literal["linear", "pow", "log"]
XAxisScale = Literal["timeseries", "linear", "pow", "log", "ordinal", "temporal"]
StackType = Literal["stacked", "normalized", "100%", None]
StackValuesDisplay = Literal["inside", "outside", None]
DisplayType = Literal[
    "line", "bar", "pie", "row", "area", "table", "scatter", 
    "map", "funnel", "combo", "waterfall", "trend", "progress", 
    "gauge", "number", "pivot table"
]

class BaseFieldRef(BaseModel):
    base_type: str = Field(alias="base-type")

class ResultMetadata(BaseModel):
    name: str
    display_name: str
    base_type: str
    field_ref: List[Union[str, Dict[str, Any]]] = Field(default_factory=list)
    semantic_type: Optional[str] = None
    
class NumberFormatting(BaseModel):
    number_style: Literal["percent", "scientific", "currency","decimal"]
    scale: Optional[float] = None
    decimals: Optional[int] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    number_separators: Optional[str] = None

    def dict(self, *args, **kwargs):
        exclude_none = kwargs.pop('exclude_none', True)
        result = self.model_dump(exclude_none=exclude_none)
        return result

class VisualizationSettings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    # Common settings
    graph_dimensions: List[str] = Field(default_factory=list, alias="graph.dimensions")
    graph_metrics: List[str] = Field(default_factory=list, alias="graph.metrics")
    graph_show_values: Optional[bool] = Field(True, alias="graph.show_values")
    
    # Axis settings
    x_axis_title: Optional[str] = Field(None, alias="graph.x_axis.title_text")
    x_axis_scale: Optional[XAxisScale] = Field(None, alias="graph.x_axis.scale")
    x_axis_enabled: Optional[Union[bool, Literal["compact", "rotate-45", "rotate-90"]]] = Field(None, alias="graph.x_axis.axis_enabled")
    y_axis_title: Optional[str] = Field(None, alias="graph.y_axis.title_text")
    y_axis_scale: Optional[YAxisScale] = Field(None, alias="graph.y_axis.scale")
    y_axis_enabled: Optional[bool] = Field(None, alias="graph.y_axis.axis_enabled")
    
    # Stacking settings
    stackable_stack_type: Optional[StackType] = Field(None, alias="stackable.stack_type")
    graph_show_stack_values: Optional[StackValuesDisplay] = Field(None, alias="graph.show_stack_values")
    
    # Pie chart settings
    pie_dimension: Optional[Union[str, List[str]]] = Field(None, alias="pie.dimension")
    pie_metric: Optional[str] = Field(None, alias="pie.metric")
    pie_show_legend: Optional[bool] = Field(None, alias="pie.show_legend")
    pie_show_labels: Optional[bool] = Field(None, alias="pie.show_labels")
    pie_percent_visibility: Optional[Literal["off", "legend", "inside", "both"]] = Field(None, alias="pie.percent_visibility")
    
    column_settings: Optional[Dict[str, NumberFormatting]] = Field(
        None,
        alias="column_settings"
    )
    
    # Trend settings
    show_trendline: Optional[bool] = Field(None, alias="graph.show_trendline")
    goal_value: Optional[float] = Field(None, alias="graph.goal_value")
    show_goal: Optional[bool] = Field(None, alias="graph.show_goal")

    def dict(self, *args, **kwargs):
        exclude_none = kwargs.pop('exclude_none', True)
        by_alias = kwargs.pop('by_alias', True)
        
        result = super().model_dump(*args, exclude_none=exclude_none, by_alias=by_alias, **kwargs)
        
        if result.get('column_settings'):
            formatted_settings = {}
            for col_name, format_settings in result['column_settings'].items():
                key = f'["name","{col_name}"]'
                formatted_settings[key] = format_settings
            result['column_settings'] = formatted_settings
            
        return {k: v for k, v in result.items() if v is not None}

class NativeQuery(BaseModel):
    query: str
    template_tags: Dict[str, Any] = Field(default_factory=dict)

class DatasetQuery(BaseModel):
    type: str = "native"
    native: NativeQuery
    database: int = 270009

class Parameter(BaseModel):
    id: Annotated[str, Field(min_length=1)]
    type: str
    name: Optional[str] = None
    slug: Optional[str] = None
    default: Optional[Any] = None

class MetabaseQuestion(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str
    dataset: bool = False
    dataset_query: DatasetQuery
    display: DisplayType
    displayIsLocked: bool = True
    visualization_settings: Any
    parameters: List[Parameter] = Field(default_factory=list)
    result_metadata: List[ResultMetadata] = Field(default_factory=list)

class LLMResponse(BaseModel):
    """Model for the raw LLM response"""
    sql: str
    explanation: str
    thought_process: List[Dict[str, str]]
    name: str
    description: str
    display_type: DisplayType
    viz_settings: Dict[str, Any] = Field(
        description="Visualization settings for Metabase question"
    )
    
    def clean_viz_settings(settings: dict) -> dict:
        """Remove null/None values from visualization settings"""
        return {
            k: v for k, v in settings.items() 
            if v is not None and (
                not isinstance(v, (list, dict)) or 
                (isinstance(v, list) and v) or
                (isinstance(v, dict) and v)
            )
        }

    @model_validator(mode='after')
    def validate_viz_settings(self):
        """Validate and clean up visualization settings based on display type"""
        display = self.display_type
        settings = self.viz_settings
        
        # Remove settings that don't apply to the current visualization type
        if display not in ["line", "bar", "area", "combo", "scatter"]:
            settings.pop("graph.x_axis.scale", None)
            settings.pop("graph.y_axis.scale", None)
        
        if display == "pie":
            # Remove non-pie settings
            keys_to_keep = ["pie.dimension", "pie.metric", "pie.show_legend", 
                          "pie.show_labels", "pie.percent_visibility"]
            self.viz_settings = {k: v for k, v in settings.items() 
                               if any(pie_key in k for pie_key in keys_to_keep)}
        
        elif display in ["number", "gauge", "progress"]:
            # Keep only relevant single-value settings
            self.viz_settings = {k: v for k, v in settings.items() 
                               if any(key in k for key in ["goal", "show_value"])}
        
        return self

class QueryResult(BaseModel):
    columns: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    affected_rows: int = 0

class ModelPreferences(BaseModel):
    hints: Optional[List[Dict[str, str]]] = None
    cost_priority: Optional[float] = None
    speed_priority: Optional[float] = None

class RawLLMContent(BaseModel):
    type: str
    text: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    input: Optional[Dict[str, Any]] = None

class Message(BaseModel):
    role: str
    content: str
    raw_llm_response: Optional[List[RawLLMContent]] = None

class MessageHistoryItem(BaseModel):
    content: str
    type: str
    timestamp: str
    raw_llm_response: Optional[List[RawLLMContent]] = None

class MessageHistory(BaseModel):
    messages: List[MessageHistoryItem]

    def decode_messages(self) -> List[Message]:
        try:
            processed_messages = []
            
            for msg in self.messages:
                if msg.type == "assistant" and msg.raw_llm_response:
                    # No need to recreate RawLLMContent objects as they're already properly typed
                    content = msg.content  # fallback to original content
                    for raw in reversed(msg.raw_llm_response):
                        if raw.type == "text" and raw.text:
                            try:
                                json_data = json.loads(raw.text)
                                if isinstance(json_data, dict):
                                    content = raw.text
                                    break
                            except json.JSONDecodeError:
                                continue
                    
                    processed_messages.append(Message(
                        role="assistant",
                        content=content,
                        raw_llm_response=msg.raw_llm_response  # Use directly
                    ))
                else:
                    # For user messages or assistant messages without raw response
                    processed_messages.append(Message(
                        role=msg.type,
                        content=msg.content
                    ))
            
            return processed_messages
        except Exception as e:
            logger.error(f"Error processing message history: {str(e)}")
            logger.error(f"Message that caused error: {msg}")
            raise ValueError(f"Failed to decode message history: {str(e)}")

QueryType = Literal["chart", "dashboard"]
class NLQuery(BaseModel):
    question: str
    database_name: str
    model_preferences: Optional[ModelPreferences] = None
    message_history: Optional[List[MessageWithToolHistory]] = None
    type: Optional[QueryType] = "chart"
    chart_id: Optional[int] = None
    
class QueryResponse(BaseModel):
    """Final response model"""
    explanation: str
    thought_process: Optional[List[Dict[str, str]]] = None
    tool_calls: List[ToolCall]
    raw_llm_response: Optional[List[RawLLMContent]] = None
    
class DashboardToolCall(BaseModel):
    type: Literal["create_chart", "update_chart", "delete_chart", "load_chart", "rearrange_dashboard", "add_markdown","preview_chart"]
    params: Dict[str, Any]