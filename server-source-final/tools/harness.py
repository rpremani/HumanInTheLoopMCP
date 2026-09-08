"""
Harness Tools for Human-in-the-Loop MCP Server

Provides tools to interact with Harness CD platform:
- Trigger deployments
- Check execution status
- Get pipeline information
- Wait for deployment completion
"""

import sys
import os
from typing import Dict, List, Optional, Any
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.harness_client import get_harness_client, HarnessClient, HarnessClientError, ExecutionStatus, DeploymentResult


async def trigger_deployment_tool(
    image_tag: str,
    target_environment: str,
    stage_identifier: str = None,
    input_set_id: str = None,
    github_branch: str = 'develop'
) -> Dict[str, Any]:
    try:
        client = get_harness_client()
        result = client.trigger_deployment(
            image_tag=image_tag,
            target_environment=target_environment,
            stage_identifier=stage_identifier,
            input_set_id=input_set_id,
            github_branch=github_branch,
        )

        return {
            'success': result.success,
            'result': asdict(result),
            'summary': _format_deployment_result(result),
        }
    except HarnessClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


def _format_deployment_result(result: DeploymentResult) -> str:
    status_emoji = '✅' if result.success else '❌'

    lines = [
        f"## Deployment {status_emoji}",
        f"**Status:** {'Triggered' if result.success else 'Failed'}",
        f"**Message:** {result.message}",
        f"**Target:** {result.target_environment}",
        f"**Image Tag:** {result.image_tag}",
    ]

    if result.execution_id:
        lines.append(f"**Execution ID:** {result.execution_id}")
    if result.harness_url:
        lines.append(f"**Harness URL:** {result.harness_url}")
    if result.error:
        lines.append(f"**Error:** {result.error}")

    return '\n'.join(lines)


async def get_execution_status_tool(execution_id: str) -> Dict[str, Any]:
    try:
        client = get_harness_client()
        status = client.get_execution_status(execution_id)

        return {
            'success': True,
            'status': asdict(status),
            'summary': _format_execution_status(status),
        }
    except HarnessClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


def _format_execution_status(status: ExecutionStatus) -> str:
    status_emoji = {
        'Success': '✅',
        'Failed': '❌',
        'Running': '🔄',
        'ApprovalWaiting': '⏳',
        'Aborted': '🚫',
    }.get(status.status, '❓')

    lines = [
        f"## Execution Status {status_emoji}",
        f"**ID:** {status.execution_id}",
        f"**Status:** {status.status}",
    ]

    if status.start_time:
        lines.append(f"**Started:** {status.start_time}")
    if status.end_time:
        lines.append(f"**Ended:** {status.end_time}")
    if status.duration:
        duration_sec = status.duration / 1000 if status.duration > 1000 else status.duration
        lines.append(f"**Duration:** {duration_sec:.0f}s")
    if status.harness_url:
        lines.append(f"**URL:** {status.harness_url}")

    if status.stages:
        lines.append('')
        lines.append('### Stages')
        for stage in status.stages:
            if stage.get('status') == 'Success':
                stage_emoji = '✅'
            elif stage.get('status') == 'Failed':
                stage_emoji = '❌'
            else:
                stage_emoji = '🔄'
            lines.append(f"- {stage_emoji} **{stage.get('name')}** - {stage.get('status')}")

    return '\n'.join(lines)


async def get_pipeline_info_tool(pipeline_id: str = None) -> Dict[str, Any]:
    try:
        client = get_harness_client()
        info = client.get_pipeline_info(pipeline_id)

        if not info:
            return {
                'success': True,
                'found': False,
                'message': 'Pipeline not found',
            }

        return {
            'success': True,
            'found': True,
            'pipeline': info,
        }
    except HarnessClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


async def wait_for_deployment_tool(
    execution_id: str,
    timeout_minutes: int = 30,
    poll_interval_seconds: int = 15
) -> Dict[str, Any]:
    try:
        client = get_harness_client()
        final_status = client.wait_for_deployment(
            execution_id=execution_id,
            timeout_minutes=timeout_minutes,
            poll_interval_seconds=poll_interval_seconds,
        )

        is_success = final_status.status == 'Success'
        is_timeout = final_status.status == 'Timeout'

        return {
            'success': is_success,
            'completed': not is_timeout,
            'timed_out': is_timeout,
            'status': asdict(final_status),
            'summary': _format_execution_status(final_status),
        }
    except HarnessClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


async def get_input_sets_tool() -> Dict[str, Any]:
    try:
        client = get_harness_client()
        input_sets = client.get_input_sets()

        return {
            'success': True,
            'count': len(input_sets),
            'input_sets': input_sets,
        }
    except HarnessClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}
