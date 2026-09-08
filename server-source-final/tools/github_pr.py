"""
PR Review Tools for Human-in-the-Loop MCP Server

Provides tools for reviewing GitHub Pull Requests:
- get_pr_for_review: Fetch comprehensive PR data
- get_file_content: Get full file content from a PR
- add_review_comment: Add a comment to a specific line
- submit_review: Submit the final PR review
"""

import sys
import os
from typing import Optional, List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.github_client import GitHubClient, GitHubClientError, PRInfo, pr_info_to_dict, get_github_client


# ============================================================
# Helper: format_pr_summary
# ============================================================

def format_pr_summary(pr_info: PRInfo) -> str:
    """Format a PRInfo object into a Markdown summary string."""

    summary_parts = []

    # Title
    summary_parts.append(f'# PR #{pr_info.number}: {pr_info.title}')
    summary_parts.append('')

    # Overview
    summary_parts.append('## Overview')
    summary_parts.append(f'- **Author:** {pr_info.author}')
    summary_parts.append(f'- **State:** {pr_info.state}')
    summary_parts.append(f'- **Branch:** `{pr_info.head_branch}` → `{pr_info.base_branch}`')
    summary_parts.append(f'- **Created:** {pr_info.created_at}')
    summary_parts.append(f'- **Updated:** {pr_info.updated_at}')
    summary_parts.append(f'- **URL:** {pr_info.url}')

    if pr_info.labels:
        summary_parts.append(f'- **Labels:** {", ".join(pr_info.labels)}')

    if pr_info.mergeable is not None:
        mergeable_str = '✅ Yes' if pr_info.mergeable else '❌ No'
        summary_parts.append(f'- **Mergeable:** {mergeable_str}')

    summary_parts.append('')

    # Changes Summary
    summary_parts.append('## Changes Summary')
    summary_parts.append(f'- **Files Changed:** {pr_info.changed_files_count}')
    summary_parts.append(f'- **Additions:** +{pr_info.additions}')
    summary_parts.append(f'- **Deletions:** -{pr_info.deletions}')
    summary_parts.append(f'- **Commits:** {pr_info.commits_count}')
    summary_parts.append('')

    # Description
    if pr_info.description:
        summary_parts.append('## Description')
        summary_parts.append(pr_info.description)
        summary_parts.append('')

    # Files Changed
    summary_parts.append('## Files Changed')

    added = [f for f in pr_info.files if f.status == 'added']
    modified = [f for f in pr_info.files if f.status == 'modified']
    deleted = [f for f in pr_info.files if f.status == 'removed']
    renamed = [f for f in pr_info.files if f.status == 'renamed']

    if added:
        summary_parts.append(f'\n### Added ({len(added)} files)')
        for f in added:
            summary_parts.append(f'- `{f.filename}` (+{f.additions})')

    if modified:
        summary_parts.append(f'\n### Modified ({len(modified)} files)')
        for f in modified:
            summary_parts.append(f'- `{f.filename}` (+{f.additions}, -{f.deletions})')

    if deleted:
        summary_parts.append(f'\n### Deleted ({len(deleted)} files)')
        for f in deleted:
            summary_parts.append(f'- `{f.filename}` (-{f.deletions})')

    if renamed:
        summary_parts.append(f'\n### Renamed ({len(renamed)} files)')
        for f in renamed:
            summary_parts.append(f'- `{f.previous_filename}` → `{f.filename}`')

    summary_parts.append('')

    # File Diffs
    summary_parts.append('## File Diffs')
    for f in pr_info.files:
        if f.patch:
            summary_parts.append(f'\n### {f.filename}')
            summary_parts.append(f'```diff\n{f.patch}\n```')

    summary_parts.append('')

    # Existing Reviews
    if pr_info.reviews:
        summary_parts.append('## Existing Reviews')
        for r in pr_info.reviews:
            state_emoji = {
                'APPROVED': '✅',
                'CHANGES_REQUESTED': '❌',
                'COMMENTED': '💬',
                'PENDING': '⏳',
            }.get(r.state, '')
            summary_parts.append(f'- {state_emoji} **{r.user}**: {r.state}')
            if r.body:
                summary_parts.append(f'  > {r.body[:200]}{"..." if len(r.body or "") > 200 else ""}')
        summary_parts.append('')

    # Existing Comments
    if pr_info.comments:
        summary_parts.append('## Existing Comments')
        for c in pr_info.comments[:10]:
            location = f' on `{c.path}` line {c.line}' if c.path else ''
            summary_parts.append(f'- **{c.user}**{location}: {c.body[:150]}{"..." if len(c.body) > 150 else ""}')

        if len(pr_info.comments) > 10:
            summary_parts.append(f'  *...and {len(pr_info.comments) - 10} more comments*')
        summary_parts.append('')

    return '\n'.join(summary_parts)


# ============================================================
# Tool: get_pr_for_review_tool
# ============================================================

async def get_pr_for_review_tool(owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
    """
    Fetch comprehensive PR data for review.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number

    Returns:
        Dictionary with summary (Markdown) and raw PR data
    """
    try:
        client = get_github_client()
        pr_info = client.get_pr_for_review(owner, repo, pr_number)

        return {
            'success': True,
            'summary': format_pr_summary(pr_info),
            'data': pr_info_to_dict(pr_info),
        }
    except GitHubClientError as e:
        return {
            'success': False,
            'error': str(e),
            'status_code': e.status_code,
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }


# ============================================================
# Tool: get_file_content_tool
# ============================================================

async def get_file_content_tool(owner: str, repo: str, pr_number: int, file_path: str, version: str = 'head') -> Dict[str, Any]:
    """
    Get the full content of a specific file from a PR.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        file_path: Path to the file
        version: "head" (PR version) or "base" (original version)

    Returns:
        Dictionary with file content
    """
    try:
        client = get_github_client()
        content = client.get_file_from_pr(owner, repo, pr_number, file_path, version)

        return {
            'success': True,
            'file_path': file_path,
            'version': version,
            'content': content,
        }
    except GitHubClientError as e:
        return {
            'success': False,
            'error': str(e),
            'status_code': e.status_code,
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }


# ============================================================
# Tool: add_review_comment_tool
# ============================================================

async def add_review_comment_tool(owner: str, repo: str, pr_number: int, file_path: str, line: int, body: str, side: str = 'RIGHT') -> Dict[str, Any]:
    """
    Add a comment to a specific line in a PR.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        file_path: Path to the file
        line: Line number
        body: Comment text
        side: Side of the diff ("LEFT" or "RIGHT")

    Returns:
        Dictionary with created comment info
    """
    try:
        client = get_github_client()

        # Get PR head commit SHA
        pr = client.get_pr(owner, repo, pr_number)
        commit_id = pr['head']['sha']

        result = client.create_review_comment(
            owner,
            repo,
            pr_number,
            body,
            commit_id,
            file_path,
            line,
            side,
        )

        return {
            'success': True,
            'comment_id': result['id'],
            'url': result.get('html_url'),
            'message': f'Comment added to {file_path} at line {line}',
        }
    except GitHubClientError as e:
        return {
            'success': False,
            'error': str(e),
            'status_code': e.status_code,
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }


# ============================================================
# Tool: submit_review_tool
# ============================================================

async def submit_review_tool(owner: str, repo: str, pr_number: int, event: str, body: str = None, comments: List[Dict] = None) -> Dict[str, Any]:
    """
    Submit a formal review on a PR.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        event: "APPROVE", "REQUEST_CHANGES", or "COMMENT"
        body: Overall review summary
        comments: Line comments to include

    Returns:
        Dictionary with review submission result
    """
    try:
        # Validate event type
        if event not in ('APPROVE', 'REQUEST_CHANGES', 'COMMENT'):
            return {
                'success': False,
                'error': f'Invalid event type: {event}. Must be APPROVE, REQUEST_CHANGES, or COMMENT',
            }

        client = get_github_client()

        # Format comments if provided
        formatted_comments = None
        if comments:
            formatted_comments = []
            for c in comments:
                formatted_comments.append({
                    'path': c['path'],
                    'line': c['line'],
                    'body': c['body'],
                    'side': c.get('side', 'RIGHT'),
                })

        result = client.create_review(
            owner,
            repo,
            pr_number,
            event,
            body,
            formatted_comments,
        )

        action_msg = {
            'APPROVE': 'approved',
            'REQUEST_CHANGES': 'requested changes on',
            'COMMENT': 'commented on',
        }[event]

        return {
            'success': True,
            'review_id': result['id'],
            'state': result['state'],
            'url': result.get('html_url'),
            'message': f'Successfully {action_msg} PR #{pr_number}',
        }
    except GitHubClientError as e:
        return {
            'success': False,
            'error': str(e),
            'status_code': e.status_code,
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }


# ============================================================
# Tool: add_pr_comment_tool
# ============================================================

async def add_pr_comment_tool(owner: str, repo: str, pr_number: int, body: str) -> Dict[str, Any]:
    """
    Add a general comment to a PR (not line-specific).

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        body: Comment text (supports Markdown)

    Returns:
        Dictionary with created comment info
    """
    try:
        client = get_github_client()
        result = client.add_issue_comment(owner, repo, pr_number, body)

        return {
            'success': True,
            'comment_id': result['id'],
            'url': result.get('html_url'),
            'message': f'Comment added to PR #{pr_number}',
        }
    except GitHubClientError as e:
        return {
            'success': False,
            'error': str(e),
            'status_code': e.status_code,
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }


# ============================================================
# Tool: merge_pr_tool
# ============================================================

async def merge_pr_tool(owner: str, repo: str, pr_number: int, merge_method: str = 'squash', commit_title: str = None, commit_message: str = None) -> Dict[str, Any]:
    """
    Merge an approved Pull Request.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        merge_method: Merge strategy - "squash" (default), "merge", or "rebase"
        commit_title: Custom title for the merge commit
        commit_message: Custom message for the merge commit

    Returns:
        Dictionary with merge result including SHA
    """
    try:
        # Validate merge method
        if merge_method not in ('merge', 'squash', 'rebase'):
            return {
                'success': False,
                'error': f"Invalid merge_method: {merge_method}. Must be 'merge', 'squash', or 'rebase'",
            }

        client = get_github_client()
        result = client.merge_pr(
            owner,
            repo,
            pr_number,
            merge_method,
            commit_title,
            commit_message,
        )

        return {
            'success': True,
            'merged': result.get('merged', False),
            'sha': result.get('sha'),
            'message': result.get('message', f'PR #{pr_number} merged successfully using {merge_method}'),
        }
    except GitHubClientError as e:
        error_msg = str(e)
        if '405' in error_msg:
            error_msg = f"PR #{pr_number} cannot be merged. Check if it's already merged, has conflicts, or requires reviews."
        elif '404' in error_msg:
            error_msg = f"PR #{pr_number} not found or you don't have permission to merge."

        return {
            'success': False,
            'error': error_msg,
            'status_code': e.status_code,
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
        }
