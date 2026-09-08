"""
DevOps Tool Registrations for Human-in-the-Loop MCP Server.

Registers tools for:
- OpenShift (get_ocp_deployment, get_ocp_pod_info, check_ocp_deployment_health, run_oc_command, ocp_login)
- Harness (trigger_harness_deployment, get_harness_execution_status, wait_for_harness_deployment, get_harness_pipeline_info)
"""

from typing import Dict

from tools.openshift import (
    get_deployment_tool,
    get_pods_tool,
    get_pod_logs_tool,
    get_pod_events_tool,
    check_deployment_health_tool,
    get_deployment_image_tag_tool,
    run_oc_command_tool,
    check_oc_login_status_tool,
    oauth_login_tool,
)

from tools.harness import (
    trigger_deployment_tool,
    get_execution_status_tool,
    get_pipeline_info_tool,
    wait_for_deployment_tool,
    get_input_sets_tool,
)


def register_devops_tools(mcp):

    @mcp.tool(name='get_ocp_deployment', description='Get information about an OpenShift deployment including image tag, replicas, and health status.')
    async def get_ocp_deployment(namespace: str, deployment_name: str):
        result = await get_deployment_tool(namespace, deployment_name)
        return result

    @mcp.tool(name='get_ocp_pod_info', description='Get comprehensive pod information including status, logs, and events.')
    async def get_ocp_pod_info(namespace: str, deployment_name: str = None, pod_name: str = None, include_logs: bool = False, include_events: bool = False, tail_lines: int = 100, container: str = None, previous: bool = False):
        result = await get_pods_tool(namespace, deployment_name)
        if not result.get('success'):
            return result
        if pod_name:
            if include_logs:
                logs_result = await get_pod_logs_tool(namespace, pod_name, container, tail_lines, previous)
                result['logs'] = logs_result.get('logs') if logs_result.get('success') else logs_result.get('error')
            if include_events:
                events_result = await get_pod_events_tool(namespace, pod_name)
                result['events'] = events_result.get('events') if events_result.get('success') else events_result.get('error')
        return result

    @mcp.tool(name='check_ocp_deployment_health', description='Comprehensive health check for an OpenShift deployment including pods and recent events.')
    async def check_ocp_deployment_health(namespace: str, deployment_name: str):
        return await check_deployment_health_tool(namespace, deployment_name)

    @mcp.tool(name='run_oc_command', description='Run an oc CLI command directly. Only read-only commands are allowed (get, describe, logs, etc.).')
    async def run_oc_command(command: str, namespace: str = None, timeout: int = 30):
        return await run_oc_command_tool(command, namespace, timeout)

    @mcp.tool(name='ocp_login', description='Check OpenShift login status and optionally perform automated browser-based OAuth login via Playwright.')
    async def ocp_login(auto_login: bool = True, api_url: str = None, username: str = None, password: str = None):
        status_result = await check_oc_login_status_tool()
        if status_result.get('logged_in'):
            return status_result
        if auto_login:
            login_result = await oauth_login_tool(api_url, username, password)
            return login_result
        return status_result

    @mcp.tool(name='trigger_harness_deployment', description='Trigger a deployment through Harness CD platform with image tag and target environment.')
    async def trigger_harness_deployment(image_tag: str, target_environment: str, stage_identifier: str = None, input_set_id: str = None, github_branch: str = "develop"):
        return await trigger_deployment_tool(image_tag, target_environment, stage_identifier, input_set_id, github_branch)

    @mcp.tool(name='get_harness_execution_status', description='Get the current status of a Harness pipeline execution.')
    async def get_harness_execution_status(execution_id: str):
        return await get_execution_status_tool(execution_id)

    @mcp.tool(name='wait_for_harness_deployment', description='Wait for a Harness deployment to complete and return final status.')
    async def wait_for_harness_deployment(execution_id: str, timeout_minutes: int = 30, poll_interval_seconds: int = 15):
        return await wait_for_deployment_tool(execution_id, timeout_minutes, poll_interval_seconds)

    @mcp.tool(name='get_harness_pipeline_info', description='Get information about a Harness pipeline, optionally including input sets.')
    async def get_harness_pipeline_info(pipeline_id: str = None, include_input_sets: bool = False):
        result = await get_pipeline_info_tool(pipeline_id)
        if include_input_sets and result.get('success'):
            input_sets_result = await get_input_sets_tool()
            if input_sets_result.get('success'):
                result['input_sets'] = input_sets_result.get('input_sets', [])
        return result
