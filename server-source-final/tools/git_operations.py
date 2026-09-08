"""
Git Operations Tools for Human-in-the-Loop MCP Server

Provides tools for Git operations:
- Clone repositories
- Create and checkout branches
- Commit and push changes
- Create pull requests
"""

import sys
import os
import subprocess
import re
from typing import Dict, List, Optional, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.github_client import get_github_client, GitHubClientError


# ============================================================
# Helper: _run_git_command
# ============================================================

def _run_git_command(command: List[str], cwd: str = None) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        return {
            'success': result.returncode == 0,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'returncode': result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Command timed out',
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


# ============================================================
# Helper: _sanitize_branch_name
# ============================================================

def _sanitize_branch_name(name: str) -> str:
    # Replace invalid characters
    sanitized = re.sub(r'[^a-zA-Z0-9_/-]', '-', name)
    # Collapse multiple dashes
    sanitized = re.sub(r'-+', '-', sanitized)
    # Strip leading/trailing dashes
    sanitized = sanitized.strip('-')
    return sanitized[:50]


# ============================================================
# Tool: clone_repository_tool
# ============================================================

async def clone_repository_tool(owner: str, repo: str, target_path: str, branch: str = None) -> Dict[str, Any]:
    """
    Clone a GitHub repository.

    Args:
        owner: Repository owner
        repo: Repository name
        target_path: Local path to clone into
        branch: Branch to checkout (optional)

    Returns:
        Dictionary with clone result
    """
    try:
        github_api_url = os.environ.get('GITHUB_API_URL', 'https://api.github.com')
        if 'github.com' in github_api_url:
            clone_url = f'https://github.com/{owner}/{repo}.git'
        else:
            # GitHub Enterprise
            base = github_api_url.replace('/api/v3', '').replace('/api', '')
            clone_url = f'{base}/{owner}/{repo}.git'

        cmd = ['git', 'clone', clone_url, target_path]
        if branch:
            cmd.extend(['--branch', branch])

        result = _run_git_command(cmd)

        if result['success']:
            return {
                'success': True,
                'message': f'Successfully cloned {owner}/{repo} to {target_path}',
                'path': target_path,
                'branch': branch or 'default',
            }
        else:
            return {
                'success': False,
                'error': result.get('stderr') or result.get('error', 'Clone failed'),
            }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }


# ============================================================
# Tool: create_branch_tool
# ============================================================

async def create_branch_tool(repo_path: str, branch_name: str, base_branch: str = None, jira_id: str = None) -> Dict[str, Any]:
    """
    Create and checkout a new branch.

    Args:
        repo_path: Path to the local repository
        branch_name: Name for the new branch
        base_branch: Base branch to create from
        jira_id: Optional JIRA ID to prefix the branch name

    Returns:
        Dictionary with branch creation result
    """
    try:
        # Build full branch name
        if jira_id:
            full_branch_name = f'{jira_id}/{_sanitize_branch_name(branch_name)}'
        else:
            full_branch_name = _sanitize_branch_name(branch_name)

        # If base branch specified, fetch and checkout it first
        if base_branch:
            fetch_result = _run_git_command(['git', 'fetch', 'origin', base_branch], cwd=repo_path)
            if not fetch_result['success']:
                return {
                    'success': False,
                    'error': f'Failed to fetch: {fetch_result.get("stderr")}',
                }

            checkout_result = _run_git_command(['git', 'checkout', base_branch], cwd=repo_path)
            if not checkout_result['success']:
                return {
                    'success': False,
                    'error': f'Failed to checkout base: {checkout_result.get("stderr")}',
                }

            _run_git_command(['git', 'pull'], cwd=repo_path)

        # Create and checkout the new branch
        result = _run_git_command(['git', 'checkout', '-b', full_branch_name], cwd=repo_path)

        if result['success']:
            return {
                'success': True,
                'message': f'Created and checked out branch: {full_branch_name}',
                'branch_name': full_branch_name,
                'base_branch': base_branch,
            }
        else:
            return {
                'success': False,
                'error': result.get('stderr') or 'Failed to create branch',
            }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }


# ============================================================
# Tool: commit_changes_tool
# ============================================================

async def commit_changes_tool(repo_path: str, message: str, files: List[str] = None) -> Dict[str, Any]:
    """
    Stage and commit changes.

    Args:
        repo_path: Path to the local repository
        message: Commit message
        files: Specific files to stage (if None, stages all)

    Returns:
        Dictionary with commit result
    """
    try:
        # Stage files
        if files:
            for file in files:
                add_result = _run_git_command(['git', 'add', file], cwd=repo_path)
                if not add_result['success']:
                    return {
                        'success': False,
                        'error': f'Failed to stage {file}: {add_result.get("stderr")}',
                    }
        else:
            add_result = _run_git_command([*('git', 'add', '-A')], cwd=repo_path)
            if not add_result['success']:
                return {
                    'success': False,
                    'error': f'Failed to stage files: {add_result.get("stderr")}',
                }

        # Check if there are changes to commit
        status_result = _run_git_command([*('git', 'status', '--porcelain')], cwd=repo_path)
        if status_result['success'] and not status_result['stdout']:
            return {
                'success': True,
                'message': 'No changes to commit',
                'committed': False,
            }

        # Commit
        commit_result = _run_git_command(['git', 'commit', '-m', message], cwd=repo_path)

        if commit_result['success']:
            # Get commit hash
            hash_result = _run_git_command([*('git', 'rev-parse', 'HEAD')], cwd=repo_path)
            commit_hash = hash_result['stdout'][:7] if hash_result['success'] else 'unknown'

            return {
                'success': True,
                'message': 'Changes committed successfully',
                'committed': True,
                'commit_hash': commit_hash,
                'commit_message': message,
            }
        else:
            return {
                'success': False,
                'error': commit_result.get('stderr') or 'Commit failed',
            }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }


# ============================================================
# Tool: push_changes_tool
# ============================================================

async def push_changes_tool(repo_path: str, branch_name: str = None, set_upstream: bool = True) -> Dict[str, Any]:
    """
    Push changes to remote.

    Args:
        repo_path: Path to the local repository
        branch_name: Branch to push (auto-detects if None)
        set_upstream: Whether to set upstream tracking

    Returns:
        Dictionary with push result
    """
    try:
        # Auto-detect branch if not provided
        if not branch_name:
            branch_result = _run_git_command([*('git', 'branch', '--show-current')], cwd=repo_path)
            if branch_result['success']:
                branch_name = branch_result['stdout']
            else:
                return {
                    'success': False,
                    'error': 'Failed to determine current branch',
                }

        # Build push command
        cmd = ['git', 'push']
        if set_upstream:
            cmd.extend(['--set-upstream', 'origin', branch_name])
        else:
            cmd.extend(['origin', branch_name])

        result = _run_git_command(cmd, cwd=repo_path)

        if result['success']:
            return {
                'success': True,
                'message': f'Successfully pushed {branch_name} to origin',
                'branch': branch_name,
            }
        else:
            return {
                'success': False,
                'error': result.get('stderr') or 'Push failed',
            }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }


# ============================================================
# Tool: create_pull_request_tool
# ============================================================

async def create_pull_request_tool(owner: str, repo: str, title: str, body: str, head: str, base: str = 'develop') -> Dict[str, Any]:
    """
    Create a pull request on GitHub.

    Args:
        owner: Repository owner
        repo: Repository name
        title: PR title
        body: PR description
        head: Source branch name
        base: Target branch (default: develop)

    Returns:
        Dictionary with PR number and URL
    """
    try:
        client = get_github_client()
        endpoint = f'/repos/{owner}/{repo}/pulls'

        data = {
            'title': title,
            'body': body,
            'head': head,
            'base': base,
        }

        response = client._post(endpoint, data=data)

        return {
            'success': True,
            'pr_number': response.get('number'),
            'pr_url': response.get('html_url'),
            'state': response.get('state'),
            'message': f'Pull request #{response.get("number")} created successfully',
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
# Tool: get_pr_checks_status_tool
# ============================================================

async def get_pr_checks_status_tool(owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
    """
    Get the status of all CI/CD checks on a pull request.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number

    Returns:
        Dictionary with check runs, statuses, and overall pass/fail status
    """
    try:
        client = get_github_client()

        # Get PR to find head SHA
        pr_endpoint = f'/repos/{owner}/{repo}/pulls/{pr_number}'
        pr_data = client._get(pr_endpoint)
        head_sha = pr_data.get('head', {}).get('sha')

        if not head_sha:
            return {
                'success': False,
                'error': 'Could not get PR head SHA',
            }

        # Get check runs
        checks_endpoint = f'/repos/{owner}/{repo}/commits/{head_sha}/check-runs'
        checks_data = client._get(checks_endpoint)

        # Get commit statuses
        status_endpoint = f'/repos/{owner}/{repo}/commits/{head_sha}/status'
        status_data = client._get(status_endpoint)

        check_runs = []
        for run in checks_data.get('check_runs', []):
            check_runs.append({
                'name': run.get('name'),
                'status': run.get('status'),
                'conclusion': run.get('conclusion'),
                'url': run.get('html_url'),
            })

        statuses = []
        for status in status_data.get('statuses', []):
            statuses.append({
                'context': status.get('context'),
                'state': status.get('state'),
                'description': status.get('description'),
                'url': status.get('target_url'),
            })

        # Determine overall status
        all_successful = all(
            r.get('conclusion') and r.get('conclusion') == 'success'
            for r in check_runs
        ) and status_data.get('state') in ('success', None)

        any_failed = any(
            r.get('conclusion') == 'failure' for r in check_runs
        ) or status_data.get('state') == 'failure'

        any_pending = any(
            r.get('status') == 'in_progress' or r.get('status') == 'queued'
            for r in check_runs
        ) or status_data.get('state') == 'pending'

        return {
            'success': True,
            'pr_number': pr_number,
            'head_sha': head_sha[:7],
            'check_runs': check_runs,
            'statuses': statuses,
            'overall': {
                'all_passed': all_successful and not any_pending,
                'any_failed': any_failed,
                'any_pending': any_pending,
            },
            'summary': _format_checks_summary(check_runs, statuses, all_successful, any_failed, any_pending),
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
# Helper: _format_checks_summary
# ============================================================

def _format_checks_summary(check_runs, statuses, all_passed, any_failed, any_pending) -> str:
    if all_passed:
        overall = ' All checks passed'
    elif any_failed:
        overall = ' Some checks failed'
    elif any_pending:
        overall = ' Checks in progress'
    else:
        overall = ' Status unknown'

    lines = [f'## PR Checks Status\n{overall}\n']

    if check_runs:
        lines.append('### Check Runs')
        for run in check_runs:
            emoji = '' if run['conclusion'] == 'success' else ('' if run['conclusion'] == 'failure' else '')
            lines.append(f'- {emoji} **{run["name"]}** - {run["conclusion"] or run["status"]}')

    if statuses:
        lines.append('\n### Commit Statuses')
        for status in statuses:
            emoji = '' if status['state'] == 'success' else ('' if status['state'] == 'failure' else '')
            lines.append(f'- {emoji} **{status["context"]}** - {status["state"]}')

    return '\n'.join(lines)
