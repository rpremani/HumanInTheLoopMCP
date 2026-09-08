"""
Git Tool Registrations for Human-in-the-Loop MCP Server.

Registers tools for:
- git_create_pr: Create pull requests via GitHub API
- get_pr_checks_status: Get CI/CD status for a PR
"""

from typing import List

from tools.git_operations import (
    create_pull_request_tool,
    get_pr_checks_status_tool,
)


def register_git_tools(mcp):

    @mcp.tool(name='git_create_pr', description='Create a pull request on GitHub. For git operations like clone, branch, commit, push - use terminal commands directly.')
    async def git_create_pr(owner: str, repo: str, title: str, body: str, head: str, base: str = "develop"):
        return await create_pull_request_tool(owner, repo, title, body, head, base)

    @mcp.tool(name='get_pr_checks_status', description='Get the status of all CI/CD checks on a pull request.')
    async def get_pr_checks_status(owner: str, repo: str, pr_number: int):
        return await get_pr_checks_status_tool(owner, repo, pr_number)
