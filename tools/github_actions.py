"""
GitHub Actions Tools for Human-in-the-Loop MCP Server

Provides tools to interact with GitHub Actions:
- Get workflow runs
- Get workflow run details and logs
- Check build status
- Trigger workflows
"""

import sys
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.github_client import get_github_client, GitHubClient, GitHubClientError


# ============================================================
# Dataclass: WorkflowRun
# ============================================================

@dataclass
class WorkflowRun:
    id: int
    name: str
    status: str
    conclusion: Optional[str]
    branch: str
    commit_sha: str
    short_sha: str
    commit_message: str
    run_number: int
    actor: str
    created_at: str
    updated_at: str
    html_url: str
    is_successful: bool
    is_failed: bool
    is_in_progress: bool
    image_tag: Optional[str] = None


# ============================================================
# Tool: get_workflow_runs_tool
# ============================================================

async def get_workflow_runs_tool(owner: str, repo: str, branch: str = None, status: str = None, per_page: int = 10) -> Dict[str, Any]:
    """
    Get recent GitHub Actions workflow runs for a repository.

    Args:
        owner: Repository owner
        repo: Repository name
        branch: Filter by branch name
        status: Filter by status: queued, in_progress, completed
        per_page: Number of results (default 10, max 100)

    Returns:
        Dictionary with workflow runs list and summary
    """
    try:
        client = get_github_client()
        endpoint = f'/repos/{owner}/{repo}/actions/runs'

        params = {'per_page': min(per_page, 100)}
        if branch:
            params['branch'] = branch
        if status:
            params['status'] = status

        response = client._get(endpoint, params=params)

        runs = []
        for run in response.get('workflow_runs', [])[:per_page]:
            runs.append(_map_workflow_run(run))

        return {
            'success': True,
            'total_count': response.get('total_count', 0),
            'runs': [asdict(r) for r in runs],
            'summary': _format_runs_summary(runs),
        }
    except GitHubClientError as e:
        return {
            'success': False,
            'error': str(e),
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }


# ============================================================
# Helper: _map_workflow_run
# ============================================================

def _map_workflow_run(run: Dict) -> WorkflowRun:
    commit_sha = run.get('head_sha', '')
    commit_message = run.get('head_commit', {}).get('message', '')

    is_successful = run.get('conclusion') == 'success'
    is_failed = run.get('conclusion') in ('failure', 'cancelled', 'timed_out')
    is_in_progress = run.get('status') in ('in_progress', 'queued')

    # Try to extract image tag from commit message
    image_tag = None
    if 'tag:' in commit_message.lower():
        import re
        match = re.search(r'tag[:\s]+([^\s]+)', commit_message, re.IGNORECASE)
        if match:
            image_tag = match.group(1)

    return WorkflowRun(
        id=run.get('id'),
        name=run.get('name', ''),
        status=run.get('status', ''),
        conclusion=run.get('conclusion'),
        branch=run.get('head_branch', ''),
        commit_sha=commit_sha,
        short_sha=commit_sha[:7] if commit_sha else '',
        commit_message=commit_message.split('\n')[0][:100],
        run_number=run.get('run_number', 0),
        actor=run.get('actor', {}).get('login', ''),
        created_at=run.get('created_at', ''),
        updated_at=run.get('updated_at', ''),
        html_url=run.get('html_url', ''),
        is_successful=is_successful,
        is_failed=is_failed,
        is_in_progress=is_in_progress,
        image_tag=image_tag,
    )


# ============================================================
# Helper: _format_runs_summary
# ============================================================

def _format_runs_summary(runs: List[WorkflowRun]) -> str:
    if not runs:
        return 'No workflow runs found.'

    lines = ['## Recent Workflow Runs\n']
    for run in runs:
        status_emoji = '' if run.is_successful else ('' if run.is_failed else '')
        lines.append(f'- {status_emoji} **#{run.run_number}** {run.branch} - {run.conclusion or run.status}')
        lines.append(f'  - Commit: {run.short_sha} - {run.commit_message[:50]}')
        lines.append(f'  - By: {run.actor} at {run.created_at}')

    return '\n'.join(lines)


# ============================================================
# Tool: get_workflow_run_details_tool
# ============================================================

async def get_workflow_run_details_tool(owner: str, repo: str, run_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific workflow run including jobs, steps, and optionally logs.

    Args:
        owner: Repository owner
        repo: Repository name
        run_id: The workflow run ID

    Returns:
        Dictionary with run details, jobs, steps
    """
    try:
        client = get_github_client()

        # Get run info
        run_endpoint = f'/repos/{owner}/{repo}/actions/runs/{run_id}'
        run_data = client._get(run_endpoint)
        run_info = _map_workflow_run(run_data)

        # Get jobs info
        jobs_endpoint = f'/repos/{owner}/{repo}/actions/runs/{run_id}/jobs'
        jobs_data = client._get(jobs_endpoint)

        jobs = []
        for job in jobs_data.get('jobs', []):
            jobs.append({
                'id': job.get('id'),
                'name': job.get('name'),
                'status': job.get('status'),
                'conclusion': job.get('conclusion'),
                'started_at': job.get('started_at'),
                'completed_at': job.get('completed_at'),
                'steps': [
                    {
                        'name': step.get('name'),
                        'status': step.get('status'),
                        'conclusion': step.get('conclusion'),
                        'number': step.get('number'),
                    }
                    for step in job.get('steps', [])
                ],
            })

        return {
            'success': True,
            'run': asdict(run_info),
            'jobs': jobs,
            'summary': _format_run_details(run_info, jobs),
        }
    except GitHubClientError as e:
        return {
            'success': False,
            'error': str(e),
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }


# ============================================================
# Helper: _format_run_details
# ============================================================

def _format_run_details(run: WorkflowRun, jobs: List[Dict]) -> str:
    status_emoji = '' if run.is_successful else ('' if run.is_failed else '')

    lines = [
        f'## Workflow Run #{run.run_number} {status_emoji}',
        f'**Status:** {run.conclusion or run.status}',
        f'**Branch:** {run.branch}',
        f'**Commit:** {run.short_sha} - {run.commit_message}',
        f'**Triggered by:** {run.actor}',
        f'**URL:** {run.html_url}',
        '',
        '### Jobs',
    ]

    for job in jobs:
        job_emoji = '' if job['conclusion'] == 'success' else ('' if job['conclusion'] == 'failure' else '')
        lines.append(f'- {job_emoji} **{job["name"]}** - {job["conclusion"] or job["status"]}')

        failed_steps = [s for s in job.get('steps', []) if s.get('conclusion') == 'failure']
        for step in failed_steps:
            lines.append(f'  -  Step {step["number"]}: {step["name"]}')

    return '\n'.join(lines)


# ============================================================
# Tool: get_workflow_run_logs_tool
# ============================================================

async def get_workflow_run_logs_tool(owner: str, repo: str, run_id: int, job_name: str = None) -> Dict[str, Any]:
    """
    Get logs for a specific workflow run.

    Args:
        owner: Repository owner
        repo: Repository name
        run_id: The workflow run ID
        job_name: Filter logs for a specific job

    Returns:
        Dictionary with job logs
    """
    try:
        client = get_github_client()

        # Get jobs for this run
        jobs_endpoint = f'/repos/{owner}/{repo}/actions/runs/{run_id}/jobs'
        jobs_data = client._get(jobs_endpoint)

        logs_result = []

        for job in jobs_data.get('jobs', []):
            if job_name and job.get('name') != job_name:
                continue

            job_id = job.get('id')
            try:
                log_endpoint = f'/repos/{owner}/{repo}/actions/jobs/{job_id}/logs'
                url = f'{client.base_url}{log_endpoint}'
                response = client.session.get(url, allow_redirects=True)

                if response.status_code == 200:
                    log_content = response.text

                    if len(log_content) > 50000:
                        log_content = log_content[:25000] + '\n\n... [TRUNCATED] ...\n\n' + log_content[-25000:]

                    logs_result.append({
                        'job_name': job.get('name'),
                        'job_id': job_id,
                        'conclusion': job.get('conclusion'),
                        'logs': log_content,
                    })
            except Exception as e:
                logs_result.append({
                    'job_name': job.get('name'),
                    'job_id': job_id,
                    'error': str(e),
                })

        return {
            'success': True,
            'run_id': run_id,
            'logs': logs_result,
        }
    except GitHubClientError as e:
        return {
            'success': False,
            'error': str(e),
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }


# ============================================================
# Tool: get_last_successful_build_tool
# ============================================================

async def get_last_successful_build_tool(owner: str, repo: str, branch: str = 'develop') -> Dict[str, Any]:
    """
    Find the last successful build for a branch.

    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch name (default: 'develop')

    Returns:
        Dictionary with the last successful build info
    """
    try:
        client = get_github_client()
        endpoint = f'/repos/{owner}/{repo}/actions/runs'

        params = {
            'branch': branch,
            'status': 'completed',
            'per_page': 50,
        }

        response = client._get(endpoint, params=params)

        for run in response.get('workflow_runs', []):
            if run.get('conclusion') == 'success':
                run_info = _map_workflow_run(run)

                return {
                    'success': True,
                    'found': True,
                    'run': asdict(run_info),
                    'message': f'Found successful build #{run_info.run_number} from {run_info.created_at}',
                }

        return {
            'success': True,
            'found': False,
            'message': f"No successful builds found for branch '{branch}' in recent history",
        }
    except GitHubClientError as e:
        return {
            'success': False,
            'error': str(e),
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }


# ============================================================
# Tool: trigger_workflow_tool
# ============================================================

async def trigger_workflow_tool(owner: str, repo: str, workflow_id: str, ref: str = 'develop', inputs: Dict = None) -> Dict[str, Any]:
    """
    Manually trigger a GitHub Actions workflow.

    Args:
        owner: Repository owner
        repo: Repository name
        workflow_id: Workflow ID or filename (e.g., 'build.yml')
        ref: Git reference to run on (default: develop)
        inputs: Workflow input parameters

    Returns:
        Dictionary with trigger confirmation
    """
    try:
        client = get_github_client()
        endpoint = f'/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches'

        data = {'ref': ref}
        if inputs:
            data['inputs'] = inputs

        client._post(endpoint, data=data)

        return {
            'success': True,
            'message': f"Workflow '{workflow_id}' triggered successfully on ref '{ref}'",
            'note': 'Check the Actions tab for the new workflow run',
        }
    except GitHubClientError as e:
        return {
            'success': False,
            'error': str(e),
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }
