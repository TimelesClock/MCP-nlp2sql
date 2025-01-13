from typing import Dict, Any, List
from abc import ABC, abstractmethod

class BaseLLMTools(ABC):
    """Base class containing tool definitions for LLM services"""
    
    @property
    def tools(self) -> List[Dict[str, Any]]:
        """Get all available tools"""
        return [
            # Chart Operations
            {
                "name": "list_charts",
                "description": """For dashboard operations only. Retrieves a list of all available charts in the collection.
                Use this to get an overview of existing charts before making modifications.""",
                "parameters": {
                    "type": "object",
                    "properties": {"requires_followup": {"type": "boolean", "description": "Indicates if the client should send the tool call result automatically"}},
                    "required": []
                }
            },
            {
                "name": "load_chart",
                "description": """For dashboard operations only. Retrieves the current configuration and metadata of an existing chart
                from Metabase. Use this before making modifications to ensure you have the latest chart settings. Essential for
                understanding the current state before updates.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chart_id": {"type": "integer", "description": "ID of the chart to load"},
                        "requires_followup": {"type": "boolean", "description": "Indicates if the client should send the tool call result automatically"}
                    },
                    "required": ["chart_id"]
                }
            },
            {
                "name": "create_chart",
                "description": "For dashboard operations only. Creates a chart and adds it to the dashboard",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "requires_followup": {"type": "boolean", "description": "Indicates if the client should send the tool call result automatically"},
                        "size_x": {"type": "integer", "minimum": 1, "maximum": 12},
                        "size_y": {"type": "integer", "minimum": 1},
                        "row": {"type": "integer", "minimum": 0},
                        "col": {"type": "integer", "minimum": 0, "maximum": 11},
                        "sql": {
                            "type": "string",
                            "description": "SQL query for the chart"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "Explanation of what the query does"
                        },
                        "name": {
                            "type": "string",
                            "description": "Clear name for the chart"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of the chart"
                        },
                        "display_type": {
                            "type": "string",
                            "enum": ["line", "bar", "pie", "row", "area", "table", "scatter", 
                                   "map", "funnel", "combo", "waterfall", "trend", "progress", 
                                   "gauge", "number", "pivot table"],
                            "description": "Type of visualization"
                        },
                        "viz_settings": {
                            "type": "object",
                            "properties": {
                                "graph.show_values": {"type": "boolean"},
                                "graph.show_stack_values": {"type": ["string", "null"]},
                                "graph.max_categories_enabled": {"type": "boolean"},
                                "graph.max_categories": {"type": ["integer", "null"]},
                                "graph.dimensions": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "graph.metrics": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "graph.x_axis.title_text": {"type": ["string", "null"]},
                                "graph.x_axis.scale": {"type": "string"},
                                "graph.x_axis.axis_enabled": {"type": ["boolean", "string"]},
                                "graph.y_axis.title_text": {"type": ["string", "null"]},
                                "graph.y_axis.scale": {"type": "string"},
                                "graph.y_axis.axis_enabled": {"type": "boolean"},
                                "graph.y_axis.min": {"type": ["number", "null"]},
                                "graph.y_axis.max": {"type": ["number", "null"]},
                                "series_settings": {"type": "object"},
                                "stackable.stack_type": {"type": ["string", "null"]},
                                "graph.goal_value": {"type": ["number", "null"]},
                                "graph.show_goal": {"type": "boolean"},
                                "graph.goal_label": {"type": ["string", "null"]},
                                "graph.show_trendline": {"type": "boolean"},
                                "pie.dimension": {
                                    "oneOf": [
                                        {"type": "string"},
                                        {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                        {"type": "null"}
                                    ]
                                },
                                "pie.metric": {"type": ["string", "null"]},
                                "pie.sort_rows": {"type": "boolean"},
                                "pie.show_legend": {"type": "boolean"},
                                "pie.show_total": {"type": "boolean"},
                                "pie.show_labels": {"type": "boolean"},
                                "pie.percent_visibility": {"type": "string"},
                                "pie.decimal_places": {"type": "integer"},
                                "pie.slice_threshold": {"type": ["number", "null"]},
                                "pie.colors": {"type": "object"},
                                "column_settings": {"type": "object"},
                                "scatter.bubble": {"type": ["string", "null"]},
                                "waterfall.increase_color": {"type": ["string", "null"]},
                                "waterfall.decrease_color": {"type": ["string", "null"]},
                                "waterfall.total_color": {"type": ["string", "null"]},
                                "waterfall.show_total": {"type": "boolean"},
                                "scalar.field": {"type": ["string", "null"]},
                                "scalar.switch_positive_negative": {"type": "boolean"},
                                "scalar.compact_primary_number": {"type": "boolean"}
                            },
                            "description": "Complete visualization settings following Metabase format"
                        }
                    },
                    "required": ["sql", "name", "description", "display_type", "viz_settings", "explanation", "thought_process", "size_x", "size_y", "row", "col"]
                }
            },
            {
                "name": "update_chart",
                "description": "For dashboard operations only. Update/edit an existing chart's properties",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "card_id": {"type": "integer", "description": "ID of the chart to update"},
                        "sql": {
                            "type": "string",
                            "description": "SQL query for the chart"
                        },
                        "name": {
                            "type": "string",
                            "description": "Clear name for the chart"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of the chart"
                        },
                        "display_type": {
                            "type": "string",
                            "enum": ["line", "bar", "pie", "row", "area", "table", "scatter", 
                                   "map", "funnel", "combo", "waterfall", "trend", "progress", 
                                   "gauge", "number", "pivot table"],
                            "description": "Type of visualization"
                        },
                        "viz_settings": {
                            "type": "object",
                            "properties": {
                                "graph.show_values": {"type": "boolean"},
                                "graph.show_stack_values": {"type": ["string", "null"]},
                                "graph.max_categories_enabled": {"type": "boolean"},
                                "graph.max_categories": {"type": ["integer", "null"]},
                                "graph.dimensions": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "graph.metrics": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "graph.x_axis.title_text": {"type": ["string", "null"]},
                                "graph.x_axis.scale": {"type": "string"},
                                "graph.x_axis.axis_enabled": {"type": ["boolean", "string"]},
                                "graph.y_axis.title_text": {"type": ["string", "null"]},
                                "graph.y_axis.scale": {"type": "string"},
                                "graph.y_axis.axis_enabled": {"type": "boolean"},
                                "graph.y_axis.min": {"type": ["number", "null"]},
                                "graph.y_axis.max": {"type": ["number", "null"]},
                                "series_settings": {"type": "object"},
                                "stackable.stack_type": {"type": ["string", "null"]},
                                "graph.goal_value": {"type": ["number", "null"]},
                                "graph.show_goal": {"type": "boolean"},
                                "graph.goal_label": {"type": ["string", "null"]},
                                "graph.show_trendline": {"type": "boolean"},
                                "pie.dimension": {
                                    "oneOf": [
                                        {"type": "string"},
                                        {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                        {"type": "null"}
                                    ]
                                },
                                "pie.metric": {"type": ["string", "null"]},
                                "pie.sort_rows": {"type": "boolean"},
                                "pie.show_legend": {"type": "boolean"},
                                "pie.show_total": {"type": "boolean"},
                                "pie.show_labels": {"type": "boolean"},
                                "pie.percent_visibility": {"type": "string"},
                                "pie.decimal_places": {"type": "integer"},
                                "pie.slice_threshold": {"type": ["number", "null"]},
                                "pie.colors": {"type": "object"},
                                "column_settings": {"type": "object"},
                                "scatter.bubble": {"type": ["string", "null"]},
                                "waterfall.increase_color": {"type": ["string", "null"]},
                                "waterfall.decrease_color": {"type": ["string", "null"]},
                                "waterfall.total_color": {"type": ["string", "null"]},
                                "waterfall.show_total": {"type": "boolean"},
                                "scalar.field": {"type": ["string", "null"]},
                                "scalar.switch_positive_negative": {"type": "boolean"},
                                "scalar.compact_primary_number": {"type": "boolean"}
                            },
                            "description": "Complete visualization settings following Metabase format"
                        },
                        "requires_followup": {"type": "boolean", "description": "Indicates if the client should send the tool call result automatically"}
                    },
                    "required": ["card_id", "sql", "name", "description", "display_type", "viz_settings", "explanation"]
                }
            },
            {
                "name": "delete_chart",
                "description": """For dashboard operations only. Permanently removes a chart from both the dashboard and
                the Metabase collection. Use with caution as this cannot be undone. Typically used during dashboard
                reorganization or cleanup.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chart_id": {"type": "integer", "description": "ID of the chart to delete"},
                        "requires_followup": {"type": "boolean", "description": "Indicates if the client should send the tool call result automatically"}
                    },
                    "required": ["chart_id"]
                }
            },
            # Dashboard Operations
            {
                "name": "rearrange_dashboard",
                "description": """For dashboard operations only. Modifies the layout and positioning of all dashboard elements.
                Use this to optimize the dashboard's visual hierarchy and organization. Can adjust the size and position of
                charts, text cards, and other dashboard elements to create a cohesive layout.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "layout": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "integer"},
                                    "size_x": {"type": "integer", "minimum": 1, "maximum": 12},
                                    "size_y": {"type": "integer", "minimum": 1},
                                    "row": {"type": "integer", "minimum": 0},
                                    "col": {"type": "integer", "minimum": 0, "maximum": 11}
                                },
                                "required": ["id", "size_x", "size_y", "row", "col"]
                            }
                        },
                        "requires_followup": {"type": "boolean", "description": "Indicates if the client should send the tool call result automatically"}
                    },
                    "required": ["layout"]
                }
            },
            {
                "name": "add_markdown",
                "description": """For dashboard operations only. Adds formatted text content to the dashboard for context
                and explanation. Use this to create headers, add descriptions, provide analysis notes, or explain dashboard
                sections. The markdown content will be rendered as a text card in the specified dashboard position.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Markdown text content"},
                        "size_x": {"type": "integer", "minimum": 1, "maximum": 12},
                        "size_y": {"type": "integer", "minimum": 1},
                        "row": {"type": "integer", "minimum": 0},
                        "col": {"type": "integer", "minimum": 0, "maximum": 11},
                        "requires_followup": {"type": "boolean", "description": "Indicates if the client should send the tool call result automatically"}
                    },
                    "required": ["content", "position"]
                }
            },
            {
                "name":"get_dashboard_cards",
                "description": """For dashboard operations only. Retrieves a list of all cards (charts, text, etc.) on the dashboard.
                Use this to get an overview of existing dashboard elements before making modifications.""",
                "parameters": {
                    "type": "object",
                    "properties": {"requires_followup": {"type": "boolean", "description": "Indicates if the client should send the tool call result automatically"}},
                    "required": []
                }
            }
        ]

    @abstractmethod
    def _convert_tools_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tools to provider-specific format"""
        pass