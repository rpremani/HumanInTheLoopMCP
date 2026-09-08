"""
GitHub Tool Registrations for Human-in-the-Loop MCP Server.

Registers tools for:
- PR Review (get_pr_for_review, get_pr_file_content, add_pr_comment, submit_pr_review, merge_pr)
- GitHub Actions (get_workflow_runs, get_workflow_run_details, trigger_workflow)
"""

from typing import List, Dict

from tools.github_pr import (
    get_pr_for_review_tool,
    get_file_content_tool,
    add_review_comment_tool,
    submit_review_tool,
    add_pr_comment_tool,
    merge_pr_tool,
)

from tools.github_actions import (
    get_workflow_runs_tool,
    get_workflow_run_details_tool,
    trigger_workflow_tool,
)


def register_github_tools(mcp):

    @mcp.tool(name='get_pr_for_review', description='Fetch comprehensive Pull Request information for review including metadata, diffs, comments, and reviews.')
    async def get_pr_for_review(owner: str, repo: str, pr_number: int):
        return await get_pr_for_review_tool(owner, repo, pr_number)

    @mcp.tool(name='get_pr_file_content', description='Get the full content of a specific file from a Pull Request. Use version="head" for PR version or "base" for original.')
    async def get_pr_file_content(owner: str, repo: str, pr_number: int, file_path: str, version: str = "head"):
        return await get_file_content_tool(owner, repo, pr_number, file_path, version)

    @mcp.tool(name='add_pr_comment', description='Add a comment to a Pull Request - either general or on a specific line. For line comments, provide file_path and line.')
    async def add_pr_comment(owner: str, repo: str, pr_number: int, body: str, file_path: str = None, line: int = None, side: str = "RIGHT"):
        if file_path and line:
            return await add_review_comment_tool(owner, repo, pr_number, file_path, line, body, side)
        return await add_pr_comment_tool(owner, repo, pr_number, body)

    @mcp.tool(name='submit_pr_review', description='Submit a formal review on a Pull Request. Event can be APPROVE, REQUEST_CHANGES, or COMMENT.')
    async def submit_pr_review(owner: str, repo: str, pr_number: int, event: str, body: str = None, comments: List[Dict] = None):
        return await submit_review_tool(owner, repo, pr_number, event, body, comments)

    @mcp.tool(name='merge_pr', description='Merge an approved Pull Request. Supports squash (default), merge, or rebase strategies.')
    async def merge_pr(owner: str, repo: str, pr_number: int, merge_method: str = "squash", commit_title: str = None, commit_message: str = None):
        return await merge_pr_tool(owner, repo, pr_number, merge_method, commit_title, commit_message)

    @mcp.tool(name='get_workflow_runs', description='Get recent GitHub Actions workflow runs. Set only_successful=True for last green build.')
    async def get_workflow_runs(owner: str, repo: str, branch: str = None, status: str = None, only_successful: bool = False, per_page: int = 10):
        if only_successful:
            from tools.github_actions import get_last_successful_build_tool
            return await get_last_successful_build_tool(owner, repo, branch or 'develop')
        return await get_workflow_runs_tool(owner, repo, branch, status, per_page)

    @mcp.tool(name='get_workflow_run_details', description='Get detailed information about a specific workflow run including jobs, steps, and optionally logs.')
    async def get_workflow_run_details(owner: str, repo: str, run_id: int, include_logs: bool = False, job_name: str = None):
        result = await get_workflow_run_details_tool(owner, repo, run_id)
        if include_logs and result.get('success'):
            from tools.github_actions import get_workflow_run_logs_tool
            logs_result = await get_workflow_run_logs_tool(owner, repo, run_id, job_name)
            if logs_result.get('success'):
                result['logs'] = logs_result.get('logs', {})
        return result

    @mcp.tool(name='trigger_workflow', description='Manually trigger a GitHub Actions workflow by ID or filename.')
    async def trigger_workflow(owner: str, repo: str, workflow_id: str, ref: str = "develop", inputs: Dict = None):
        return await trigger_workflow_tool(owner, repo, workflow_id, ref, inputs)
