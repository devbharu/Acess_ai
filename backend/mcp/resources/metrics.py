"""
System evaluation metrics resource for AccessAI MCP Server.
URI format: accessai://metrics/summary
"""

from typing import Dict, Any, Optional
from ...services.metrics_service import MetricsService


def get_metrics_resource(context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return MetricsService.get_metrics_dashboard()
