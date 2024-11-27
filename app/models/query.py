from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class ModelPreferences(BaseModel):
    hints: Optional[List[Dict[str, str]]] = None
    cost_priority: Optional[float] = None
    speed_priority: Optional[float] = None
    intelligence_priority: Optional[float] = None

class NLQuery(BaseModel):
    question: str
    model_preferences: Optional[ModelPreferences] = None

class QueryResult(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    affected_rows: int

class QueryResponse(BaseModel):
    sql: str
    result: QueryResult
    explanation: str
    thought_process: List[Dict[str, str]]

class SchemaAnalysis(BaseModel):
    relevant_tables: List[str]
    relationships: List[Dict[str, str]]
    sample_data_insights: Dict[str, Any]