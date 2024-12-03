from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, conint
from enum import Enum

class DisplayType(str, Enum):
    line = "line"
    bar = "bar"
    pie = "pie"
    row = "row"
    area = "area"
    table = "table"
    scatter = "scatter"
    map = "map"
    funnel = "funnel"

class BaseType(str, Enum):
    Text = "type/Text"
    Integer = "type/Integer"
    Float = "type/Float"
    Boolean = "type/Boolean"
    DateTime = "type/DateTime"
    Date = "type/Date"
    Time = "type/Time"
    JSON = "type/JSON"

class DateTimeFingerprint(BaseModel):
    earliest: Optional[str] = None
    latest: Optional[str] = None

class TextFingerprint(BaseModel):
    percent_json: Optional[float] = Field(None, alias="percent-json")
    percent_url: Optional[float] = Field(None, alias="percent-url")
    percent_email: Optional[float] = Field(None, alias="percent-email")
    percent_state: Optional[float] = Field(None, alias="percent-state")
    average_length: Optional[float] = Field(None, alias="average-length")

class NumberFingerprint(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    avg: Optional[float] = None
    q1: Optional[float] = None
    q3: Optional[float] = None
    sd: Optional[float] = None

class FingerprintType(BaseModel):
    type_DateTime: Optional[DateTimeFingerprint] = Field(None, alias="type/DateTime")
    type_Text: Optional[TextFingerprint] = Field(None, alias="type/Text")
    type_Number: Optional[NumberFingerprint] = Field(None, alias="type/Number")
    experimental: Dict[str, Any] = Field(default_factory=dict)

class GlobalFingerprint(BaseModel):
    distinct_count: Optional[int] = Field(None, alias="distinct-count")
    nil_percent: Optional[float] = Field(None, alias="nil%")

class Fingerprint(BaseModel):
    global_: GlobalFingerprint = Field(alias="global")
    type: FingerprintType

class BaseFieldRef(BaseModel):
    base_type: str = Field(alias="base-type")

class FieldRef(BaseModel):
    field: list = ["field"]
    name: str
    options: BaseFieldRef

class ResultMetadata(BaseModel):
    description: Optional[str] = None
    semantic_type: Optional[str] = None
    name: str
    field_ref: List[Union[str, Dict[str, Any]]]
    id: Optional[conint(gt=0)] = None
    display_name: str
    fingerprint: Optional[Fingerprint] = None
    base_type: str

class NativeQuery(BaseModel):
    query: str
    template_tags: Dict[str, Any] = Field(default_factory=dict)

class DatasetQuery(BaseModel):
    type: str = "native"
    native: NativeQuery
    database: int = 270009

class VisualizationSettings(BaseModel):
    graph_dimensions: List[str] = Field(default_factory=list, alias="graph.dimensions")
    graph_metrics: List[str] = Field(default_factory=list, alias="graph.metrics")
    graph_show_values: bool = Field(default=True, alias="graph.show_values")
    stackable_stack_type: Optional[str] = Field(None, alias="stackable.stack_type")
    
class ParameterTarget(BaseModel):
    field_ref: List[Union[str, Dict[str, Any]]] = Field(alias="field-ref")

class ParameterMappings(BaseModel):
    parameter_id: str = Field(..., alias="parameter_id")
    target: Union[List[Union[str, Dict[str, Any]]], Dict[str, Any]]
    card_id: Optional[conint(gt=0)] = None

class ValuesSourceConfig(BaseModel):
    values: Optional[List[Any]] = None
    card_id: Optional[conint(gt=0)] = None
    value_field: Optional[List[Union[str, Dict[str, Any]]]] = None
    label_field: Optional[List[Union[str, Dict[str, Any]]]] = None

class Parameter(BaseModel):
    id: str = Field(..., min_length=1)
    type: str
    name: Optional[str] = None
    slug: Optional[str] = None
    default: Optional[Any] = None
    values_source_type: Optional[str] = None
    values_source_config: Optional[ValuesSourceConfig] = None
    sectionId: Optional[str] = None

class MetabaseQuestion(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    dataset: bool = False
    dataset_query: DatasetQuery
    display: DisplayType
    displayIsLocked: bool = True
    visualization_settings: VisualizationSettings
    parameters: List[Parameter] = Field(default_factory=list)
    parameter_mappings: List[ParameterMappings] = Field(default_factory=list)
    archived: bool = False
    enable_embedding: bool = False
    embedding_params: Optional[Dict[str, Any]] = None
    collection_id: Optional[conint(gt=0)] = None
    collection_position: Optional[conint(gt=0)] = None
    collection_preview: bool = True
    cache_ttl: Optional[conint(gt=0)] = None
    result_metadata: List[ResultMetadata] = Field(default_factory=list)

class ModelPreferences(BaseModel):
    hints: Optional[List[Dict[str, str]]] = None
    cost_priority: Optional[float] = None
    speed_priority: Optional[float] = None
    intelligence_priority: Optional[float] = None

class NLQuery(BaseModel):
    question: str
    model_preferences: Optional[ModelPreferences] = None

class QueryResult(BaseModel):
    columns: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    affected_rows: int = 0

class QueryResponse(BaseModel):
    sql: str
    result: QueryResult
    explanation: str
    thought_process: List[Dict[str, str]]
    metabase_question: MetabaseQuestion

class SchemaAnalysis(BaseModel):
    relevant_tables: List[str]
    relationships: List[Dict[str, str]]
    sample_data_insights: Dict[str, Any]