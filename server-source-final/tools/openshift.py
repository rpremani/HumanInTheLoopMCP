"""
OpenShift Tools for Human-in-the-Loop MCP Server

Provides tools to interact with OpenShift/Kubernetes clusters:
- Get deployment information
- List and inspect pods
- Get pod logs and events
- Check deployment health
- Run oc CLI commands directly
"""

import sys
import os
from typing import Dict, List, Optional, Any
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.openshift_client import get_openshift_client, OpenShiftClient, OpenShiftClientError, DeploymentInfo, PodInfo, validate_oc_session


async def get_deployment_tool(namespace: str, deployment_name: str) -> Dict[str, Any]:
    try:
        client = get_openshift_client()
        deployment = client.get_deployment(namespace, deployment_name)

        if not deployment:
            return {
                'success': True,
                'found': False,
                'message': f"Deployment '{deployment_name}' not found in namespace '{namespace}'",
            }

        return {
            'success': True,
            'found': True,
            'deployment': asdict(deployment),
            'summary': _format_deployment_summary(deployment),
        }
    except OpenShiftClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


def _format_deployment_summary(dep: DeploymentInfo) -> str:
    status_emoji = '✅' if dep.is_healthy else ('⚠️' if dep.is_degraded else '❌')

    lines = [
        f"## Deployment: {dep.name} {status_emoji}",
        f"**Namespace:** {dep.namespace}",
        f"**Status:** {dep.status}",
        f"**Image Tag:** {dep.image_tag or 'N/A'}",
        f"**Replicas:** {dep.replicas_ready}/{dep.replicas_desired} ready",
        f"**Health:** {dep.health_percentage:.0f}%",
    ]

    if dep.pods_url:
        lines.append(f"**View Pods:** {dep.pods_url}")

    return '\n'.join(lines)


async def list_deployments_tool(namespace: str) -> Dict[str, Any]:
    try:
        client = get_openshift_client()
        deployments = client.list_deployments(namespace)

        return {
            'success': True,
            'count': len(deployments),
            'deployments': [asdict(d) for d in deployments],
            'summary': _format_deployments_list(deployments),
        }
    except OpenShiftClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


def _format_deployments_list(deployments: List[DeploymentInfo]) -> str:
    if not deployments:
        return 'No deployments found in namespace.'

    lines = ['## Deployments\n']
    for dep in deployments:
        status_emoji = '✅' if dep.is_healthy else ('⚠️' if dep.is_degraded else '❌')
        lines.append(f"- {status_emoji} **{dep.name}** - {dep.replicas_ready}/{dep.replicas_desired} replicas - {dep.image_tag or 'N/A'}")

    return '\n'.join(lines)


async def get_pods_tool(namespace: str, deployment_name: str = None) -> Dict[str, Any]:
    try:
        client = get_openshift_client()
        pods = client.get_pods(namespace, deployment_name)

        return {
            'success': True,
            'count': len(pods),
            'pods': [asdict(p) for p in pods],
            'summary': _format_pods_list(pods),
        }
    except OpenShiftClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


def _format_pods_list(pods: List[PodInfo]) -> str:
    if not pods:
        return 'No pods found.'

    lines = ['## Pods\n']
    for pod in pods:
        status_emoji = '✅' if pod.ready else ('⏳' if pod.status == 'Pending' else '❌')
        restart_info = f' (⚠ {pod.restart_count} restarts)' if pod.restart_count > 0 else ''
        lines.append(f"- {status_emoji} **{pod.name}** - {pod.status}{restart_info}")
        if pod.node:
            lines.append(f"  - Node: {pod.node}")

    return '\n'.join(lines)


async def get_pod_logs_tool(
    namespace: str,
    pod_name: str,
    container: str = None,
    tail_lines: int = 100,
    previous: bool = False
) -> Dict[str, Any]:
    try:
        client = get_openshift_client()
        logs = client.get_pod_logs(namespace, pod_name, container, tail_lines, previous)

        return {
            'success': True,
            'pod_name': pod_name,
            'namespace': namespace,
            'container': container,
            'tail_lines': tail_lines,
            'previous': previous,
            'logs': logs,
        }
    except OpenShiftClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


async def get_pod_events_tool(namespace: str, pod_name: str = None) -> Dict[str, Any]:
    try:
        client = get_openshift_client()
        events = client.get_pod_events(namespace, pod_name)

        return {
            'success': True,
            'count': len(events),
            'events': events,
            'summary': _format_events_list(events),
        }
    except OpenShiftClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


def _format_events_list(events: List[Dict]) -> str:
    if not events:
        return 'No events found.'

    lines = ['## Recent Events\n']
    for event in events[:20]:
        type_emoji = '⚠️' if event.get('type') == 'Warning' else 'ℹ️'
        count_info = f' (x{event.get("count")})' if event.get('count', 1) > 1 else ''
        lines.append(f"- {type_emoji} **{event.get('reason')}**{count_info}")
        lines.append(f"  - {event.get('message', 'No message')[:200]}")
        if event.get('involved_object'):
            lines.append(f"  - Object: {event.get('involved_object')}")

    return '\n'.join(lines)


async def check_deployment_health_tool(namespace: str, deployment_name: str) -> Dict[str, Any]:
    try:
        client = get_openshift_client()
        health = client.check_deployment_health(namespace, deployment_name)

        result = {'success': True}
        result.update(health)
        result.update({'summary': _format_health_summary(health)})
        return result
    except OpenShiftClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


def _format_health_summary(health: Dict) -> str:
    if not health.get('found'):
        return health.get('message', 'Deployment not found')

    status_emoji = '✅' if health.get('healthy') else '❌'
    pods = health.get('pods', {})

    lines = [
        f"## Health Check {status_emoji}",
        f"**Status:** {health.get('status')}",
        f"**Message:** {health.get('message')}",
        '',
        '### Pod Summary',
        f"- Total: {pods.get('total', 0)}",
        f"- Running: {pods.get('running', 0)}",
        f"- Ready: {pods.get('ready', 0)}",
        f"- Pending: {pods.get('pending', 0)}",
        f"- Crashed (>5 restarts): {pods.get('crashed', 0)}",
    ]

    warnings = health.get('recent_warnings', [])
    if warnings:
        lines.append('')
        lines.append('### Recent Warnings')
        for w in warnings[:5]:
            lines.append(f"- ⚠ {w.get('reason')}: {w.get('message', '')[:100]}")

    return '\n'.join(lines)


async def get_deployment_image_tag_tool(namespace: str, deployment_name: str) -> Dict[str, Any]:
    try:
        client = get_openshift_client()
        deployment = client.get_deployment(namespace, deployment_name)

        if not deployment:
            return {
                'success': True,
                'found': False,
                'message': f"Deployment '{deployment_name}' not found",
            }

        return {
            'success': True,
            'found': True,
            'deployment_name': deployment_name,
            'namespace': namespace,
            'image_tag': deployment.image_tag,
            'status': deployment.status,
            'healthy': deployment.is_healthy,
        }
    except OpenShiftClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


async def run_oc_command_tool(
    command: str,
    namespace: str = None,
    timeout: int = 30
) -> Dict[str, Any]:
    import subprocess

    cmd_parts = ['oc']

    if namespace:
        cmd_parts.extend(['-n', namespace])

    cmd_parts.extend(command.split())

    dangerous_commands = ['delete', 'apply', 'create', 'patch', 'edit', 'replace']
    if any(dc in command.lower() for dc in dangerous_commands):
        return {
            'success': False,
            'error': 'Dangerous command detected. Only read-only commands are allowed through this tool.',
            'hint': "Use 'get', 'describe', 'logs', 'status' type commands instead.",
        }

    try:
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output = result.stdout
        if len(output) > 10000:
            output = output[:10000] + '\n\n... [output truncated, use more specific filters]'

        stderr = result.stderr
        if len(stderr) > 2000:
            stderr = stderr[:2000] + '\n... [truncated]'

        return {
            'success': result.returncode == 0,
            'command': ' '.join(cmd_parts),
            'return_code': result.returncode,
            'output': output,
            'stderr': stderr if result.returncode != 0 else None,
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': f'Command timed out after {timeout} seconds',
            'command': ' '.join(cmd_parts),
        }
    except FileNotFoundError:
        return {
            'success': False,
            'error': 'oc command not found. Make sure OpenShift CLI is installed and in PATH.',
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Failed to run command: {str(e)}',
            'command': ' '.join(cmd_parts),
        }


async def check_oc_login_status_tool() -> Dict[str, Any]:
    import subprocess

    try:
        server_config_result = subprocess.run(
            ['oc', 'config', 'view', '--minify', '-o', 'jsonpath={.clusters[0].cluster.server}'],
            capture_output=True,
            text=True,
            timeout=10,
        )

        configured_server = server_config_result.stdout.strip() if server_config_result.returncode == 0 and server_config_result.stdout.strip() else None

        user_result = subprocess.run(
            ['oc', 'whoami'],
            capture_output=True,
            text=True,
            timeout=10,
        )

        server_result = subprocess.run(
            ['oc', 'whoami', '--show-server'],
            capture_output=True,
            text=True,
            timeout=10,
        )

        project_result = subprocess.run(
            ['oc', 'project', '-q'],
            capture_output=True,
            text=True,
            timeout=10,
        )

        is_logged_in = user_result.returncode == 0
        token_valid = is_logged_in

        server = server_result.stdout.strip() if server_result.returncode == 0 else configured_server

        return {
            'success': True,
            'logged_in': is_logged_in,
            'token_valid': token_valid,
            'user': user_result.stdout.strip() if is_logged_in else None,
            'server': server,
            'configured_server': configured_server,
            'current_project': project_result.stdout.strip() if project_result.returncode == 0 else None,
            'summary': _format_login_status(
                is_logged_in,
                user_result.stdout.strip() if is_logged_in else None,
                server,
                project_result.stdout.strip() if project_result.returncode == 0 else None,
                token_valid,
                configured_server,
            ),
        }
    except FileNotFoundError:
        return {
            'success': False,
            'logged_in': False,
            'error': 'oc command not found. Make sure OpenShift CLI is installed.',
        }
    except Exception as e:
        return {
            'success': False,
            'logged_in': False,
            'error': f'Failed to check login status: {str(e)}',
        }


def _format_login_status(
    logged_in: bool,
    user: str,
    server: str,
    project: str,
    token_valid: bool = True,
    configured_server: str = None
) -> str:
    if not logged_in:
        lines = [
            '## OpenShift Status ❌\n',
            '**Not logged in** - Token expired or invalid\n',
        ]

        if configured_server:
            lines.append(f'**Configured Server:** `{configured_server}`\n')
            lines.append('Run the following to re-authenticate:')
            lines.append('```')
            lines.append(f'oc login {configured_server}')
            lines.append('```')
        else:
            lines.append('Run `oc login <server-url>` to authenticate with your OpenShift cluster.')

        return '\n'.join(lines)

    return (
        f"## OpenShift Status ✅\n\n**User:** `{user}`\n"
        f"**Server:** `{server}`\n"
        f"**Current Project:** `{project or 'none'}`\n\n"
        f"You are logged in and ready to use OpenShift tools.\n"
    )


async def oauth_login_tool(
    api_url: str = None,
    username: str = None,
    password: str = None,
    headless: bool = None
) -> Dict[str, Any]:
    import os

    api_url = api_url or os.environ.get('OPENSHIFT_API_URL') or os.environ.get('OPENSHIFT_CONSOLE_URL')
    username = username or os.environ.get('OPENSHIFT_USERNAME')
    password = password or os.environ.get('OPENSHIFT_PASSWORD')

    if headless is None:
        headless_env = os.environ.get('OPENSHIFT_HEADLESS', 'true').lower()
        headless = headless_env != 'false'

    if not api_url:
        return {
            'success': False,
            'error': 'api_url is required (or set OPENSHIFT_API_URL or OPENSHIFT_CONSOLE_URL environment variable)',
        }

    if not username:
        return {
            'success': False,
            'error': 'username is required (or set OPENSHIFT_USERNAME environment variable)',
        }

    if not password:
        return {
            'success': False,
            'error': 'password is required (or set OPENSHIFT_PASSWORD environment variable)',
        }

    try:
        from utils.openshift_oauth import login_and_get_token

        result = await login_and_get_token(
            api_url,
            username,
            password,
            headless=headless,
        )

        if result.success:
            return {
                'success': True,
                'message': 'Successfully logged in to OpenShift',
                'server': api_url,
                'token_preview': result.token[:20] + '...' if result.token else None,
                'summary': (
                    f"## OpenShift Login Successful ✅\n\n**Server:** `{api_url}`\n"
                    f"**Token:** `{result.token[:20]}...`\n\n"
                    f"You are now logged in. OpenShift tools are ready to use.\n"
                ),
            }

        return {
            'success': False,
            'error': result.error,
            'server': api_url,
        }
    except ImportError as e:
        return {
            'success': False,
            'error': (
                f'Playwright dependency is missing at runtime. Install it in the Python environment '
                f'used to run the MCP server: pip install playwright. This OpenShift login flow uses '
                f'your system-installed Chrome (no Playwright Chromium download required). '
                f'(ImportError: {e})'
            ),
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'OAuth login failed: {str(e)}',
        }
