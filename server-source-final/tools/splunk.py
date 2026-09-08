"""
Splunk Tools for Human-in-the-Loop MCP Server

Provides tools to search and analyze logs in Splunk:
- Search for errors and exceptions
- Get logs by trace ID
- Get error summaries
- Custom log searches
"""

import sys
import os
from typing import Dict, List, Optional, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.splunk_client import get_splunk_client, SplunkClient, SplunkClientError, SearchResult


async def search_logs_tool(
    query: str,
    time_range: str = '-1h',
    max_results: int = 50
) -> Dict[str, Any]:
    try:
        client = get_splunk_client()
        result = client.search(
            query,
            time_range,
            max_results=max_results,
        )

        truncated_events = []
        for event in result.events:
            truncated = {}
            for key, value in event.items():
                if isinstance(value, str) and len(value) > 500:
                    truncated[key] = value[:500] + '...[truncated]'
                else:
                    truncated[key] = value
            truncated_events.append(truncated)

        return {
            'success': True,
            'total_count': result.total_count,
            'events': truncated_events,
            'summary': _format_search_summary(result),
        }
    except SplunkClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


def _format_search_summary(result: SearchResult) -> str:
    lines = [f"## Search Results ({result.total_count} events)\n"]

    if not result.events:
        lines.append('No events found matching the query.')
        return '\n'.join(lines)

    for i, event in enumerate(result.events[:10]):
        time_field = event.get('_time', 'unknown time')
        raw = event.get('_raw', '')
        if len(raw) > 200:
            raw = raw[:200] + '...'
        lines.append(f"**{i + 1}. [{time_field}]**")
        lines.append(f"```\n{raw}\n```")

    if result.total_count > 10:
        lines.append(f"\n*...and {result.total_count - 10} more events*")

    return '\n'.join(lines)


async def search_errors_tool(
    index: str = None,
    source: str = None,
    host: str = None,
    time_range: str = '-1h',
    max_results: int = 30
) -> Dict[str, Any]:
    try:
        client = get_splunk_client()
        result = client.search_errors(
            index=index,
            source=source,
            host=host,
            time_range=time_range,
            max_results=max_results,
        )

        return {
            'success': True,
            'error_count': result.total_count,
            'errors': _extract_error_info(result.events),
            'summary': _format_errors_summary(result),
        }
    except SplunkClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


def _extract_error_info(events: List[Dict]) -> List[Dict]:
    errors = []
    for event in events:
        errors.append({
            'time': event.get('_time'),
            'host': event.get('host'),
            'source': event.get('source', '').split('/')[-1],
            'message': _truncate(event.get('_raw', ''), 300),
        })
    return errors


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + '...'


def _format_errors_summary(result: SearchResult) -> str:
    lines = [f"## Error Logs ({result.total_count} found)\n"]

    if not result.events:
        lines.append('✅ No errors found in the specified time range!')
        return '\n'.join(lines)

    lines.append('⚠️ Errors detected:\n')

    for i, event in enumerate(result.events[:15]):
        time_field = event.get('_time', '?')
        host = event.get('host', '?')
        raw = event.get('_raw', '')

        error_line = raw.split('\n')[0][:150]

        lines.append(f"**{i + 1}.** `{time_field}` on `{host}`")
        lines.append(f"   {error_line}")

    if result.total_count > 15:
        lines.append(f"\n*...and {result.total_count - 15} more errors*")

    return '\n'.join(lines)


async def search_by_trace_id_tool(
    trace_id: str,
    index: str = None,
    time_range: str = '-1h'
) -> Dict[str, Any]:
    try:
        client = get_splunk_client()
        result = client.search_by_trace_id(trace_id, index, time_range)

        return {
            'success': True,
            'trace_id': trace_id,
            'event_count': result.total_count,
            'events': _extract_trace_events(result.events),
            'summary': _format_trace_summary(trace_id, result),
        }
    except SplunkClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


def _extract_trace_events(events: List[Dict]) -> List[Dict]:
    extracted = []
    for event in events:
        extracted.append({
            'time': event.get('_time'),
            'source': event.get('source', '').split('/')[-1],
            'message': _truncate(event.get('_raw', ''), 400),
        })
    return extracted


def _format_trace_summary(trace_id: str, result: SearchResult) -> str:
    lines = [
        f"## Trace: `{trace_id}`",
        f"**Events found:** {result.total_count}",
        '',
    ]

    if not result.events:
        lines.append('No events found for this trace ID.')
        return '\n'.join(lines)

    lines.append('### Event Timeline')

    for event in result.events[:20]:
        time_field = event.get('_time', '?')
        source = event.get('source', '?').split('/')[-1]
        raw = event.get('_raw', '')[:200]

        is_error = any(err in raw.upper() for err in ('ERROR', 'EXCEPTION', 'FATAL'))
        emoji = '❌' if is_error else '📝'

        lines.append(f"{emoji} **{time_field}** - `{source}`")
        lines.append(f"   {raw[:150]}")

    return '\n'.join(lines)


async def get_error_summary_tool(
    index: str = None,
    source: str = None,
    time_range: str = '-1h'
) -> Dict[str, Any]:
    try:
        client = get_splunk_client()
        result = client.get_error_summary(index, source, time_range)

        return {
            'success': True,
            'total_errors': result['total_errors'],
            'by_type': result['by_type'],
            'summary': _format_error_summary(result),
        }
    except SplunkClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


def _format_error_summary(result: Dict) -> str:
    lines = [
        '## Error Summary',
        f"**Total Errors:** {result['total_errors']}",
        '',
    ]

    if not result['by_type']:
        lines.append('No categorized errors found.')
        return '\n'.join(lines)

    lines.append('### By Error Type')

    for item in result['by_type']:
        error_type = item.get('error_type', 'Unknown')
        count = item.get('count', 0)
        lines.append(f"- **{error_type}**: {count}")

    return '\n'.join(lines)


async def search_application_logs_tool(
    app_name: str,
    log_level: str = None,
    time_range: str = '-1h',
    max_results: int = 50
) -> Dict[str, Any]:
    try:
        client = get_splunk_client()

        query = f'"{app_name}"'
        if log_level:
            query += f' {log_level}'
        query += f' | head {max_results}'

        result = client.search(
            query,
            time_range,
            max_results=max_results,
        )

        return {
            'success': True,
            'app_name': app_name,
            'log_count': result.total_count,
            'logs': _extract_error_info(result.events),
            'summary': _format_search_summary(result),
        }
    except SplunkClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}
