"""
Observability Tool Registrations for Human-in-the-Loop MCP Server.

Registers tools for:
- Splunk (splunk_search, splunk_trace_search)
"""

from typing import Optional

from tools.splunk import (
    search_logs_tool,
    search_errors_tool,
    search_by_trace_id_tool,
    get_error_summary_tool,
    search_application_logs_tool,
)


def register_observability_tools(mcp):

    @mcp.tool(name='splunk_search', description='Search Splunk logs with various search types: custom, errors, error_summary, or app.')
    async def splunk_search(query: str = None, app_name: str = None, search_type: str = "custom", index: str = None, source: str = None, host: str = None, log_level: str = None, time_range: str = "-1h", max_results: int = 50):
        if search_type == 'errors':
            return await search_errors_tool(
                index=index, source=source, host=host, time_range=time_range, max_results=max_results
            )
        elif search_type == 'error_summary':
            return await get_error_summary_tool(
                index=index, source=source, time_range=time_range
            )
        elif search_type == 'app' and app_name:
            return await search_application_logs_tool(
                app_name=app_name, log_level=log_level, time_range=time_range, max_results=max_results
            )
        elif search_type == 'custom' and query:
            return await search_logs_tool(
                query=query, time_range=time_range, max_results=max_results
            )
        elif query:
            return await search_logs_tool(query, time_range, max_results)
        elif app_name:
            return await search_application_logs_tool(app_name, log_level, time_range, max_results)
        else:
            return {"success": False, "error": "Either 'query' or 'app_name' is required, or use search_type='errors'/'error_summary'"}

    @mcp.tool(name='splunk_trace_search', description='Search Splunk logs by trace/correlation ID to follow a request flow across services.')
    async def splunk_trace_search(trace_id: str, index: str = None, time_range: str = "-1h"):
        return await search_by_trace_id_tool(trace_id, index, time_range)
