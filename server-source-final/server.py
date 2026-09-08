"""
Human-in-the-Loop MCP Server

A Model Context Protocol server that provides:
- Human-in-the-loop feedback tool for AI agent workflows
- DevOps tools (OpenShift, Harness)
- GitHub tools (PR Review, Actions)
- Git operations (Branch, Commit, PR)
- Quality tools (SonarQube) - Checkmarx disabled
- Observability tools (Splunk)
- RAG tools (Document indexing, Semantic search)

Tool count: 27 tools (4 tools disabled: Checkmarx)
"""

import os
import sys
import subprocess
import json
from typing import List, Dict, Optional
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()


# Determine application path (handles PyInstaller frozen exe vs script)
if getattr(sys, 'frozen', False):

    application_path = os.path.dirname(sys.executable)

else:
    application_path = os.path.dirname(os.path.abspath(__file__))

FEEDBACK_UI_PATH = os.getenv('HITL_FEEDBACK_UI_PATH') or os.path.join(application_path, 'feedback-ui.exe')

if not getattr(sys, 'frozen', False) and not os.path.exists(FEEDBACK_UI_PATH):
    FEEDBACK_UI_PATH = os.path.join(application_path, 'dist', 'feedback-ui.exe')


sys.path.insert(0, application_path)

mcp = FastMCP('Human-in-the-Loop MCP Server')






@mcp.prompt(name='use_human_feedback', description='Instructions for using human-in-the-loop workflow')
async def use_human_feedback_prompt():
    """
    Provides instructions for implementing human-in-the-loop workflow in AI interactions.
    """
    return (
        "#Important For this task\n"
        "Whenever you want to ask a question, always call the MCP human_in_the_loop.\n"
        "Whenever you're about to complete a user request, call the MCP human_in_the_loop "
        "instead of simply ending the process. Keep calling MCP until the user's feedback "
        "is empty, then end the request."
    )


@mcp.tool(name='human_in_the_loop', description='''
    Human-in-the-loop feedback tool that displays project information to the user via a desktop UI
    and waits for their feedback. This tool opens a WPF application with the provided summary and
    project path, allowing the user to provide feedback on the current work.

    Args:
        summary (str): Summary of what has been done in the project so far. Supports Markdown formatting.
        path (str): Path of the project where the client currently operates.
        suggested_actions (list[str], optional): List of suggested next actions that will be displayed 
            as clickable pill-shaped buttons in the UI under "Quick Actions:". When the user clicks 
            a button, the action text is auto-populated in the feedback textbox for quick submission.
            Example: ["Run all tests", "Deploy to staging", "Review changes", "Add documentation"]
            Best practice: Include 2-5 concise, actionable suggestions based on the current context.

    Returns:
        str: The user's feedback response. Returns empty string if user provides no feedback.
    
    Example usage:
        human_in_the_loop(
            summary="## Task Complete\\n\\nImplemented the new feature successfully.",
            path="c:/projects/my-app",
            suggested_actions=["Run tests", "Deploy", "Add more features"]
        )
''')
async def human_in_the_loop(summary: str, path: str, suggested_actions: list[str] = None):
    """
    Display project summary and path to the user via desktop UI and wait for their feedback.
    Uses the WPF feedback application to show the information and collect user input.
    """
    try:
        if not os.path.exists(FEEDBACK_UI_PATH):
            return f"Error: Feedback UI executable not found at {FEEDBACK_UI_PATH}"

        cmd_args = [FEEDBACK_UI_PATH, summary, path]

        if FEEDBACK_UI_PATH.lower().endswith('.dll'):
            cmd_args.insert(0, 'dotnet')

        if suggested_actions:
            cmd_args.append(json.dumps(suggested_actions))

        result = subprocess.run(cmd_args, capture_output=True, text=True)

        if result.returncode == 0:
            raw_output = result.stdout.strip()

            if 'MCP_RESPONSE_START' in raw_output and 'MCP_RESPONSE_END' in raw_output:
                start_marker = 'MCP_RESPONSE_START'
                end_marker = 'MCP_RESPONSE_END'

                start_idx = raw_output.find(start_marker)
                if start_idx != -1:
                    start_idx += len(start_marker)
                    end_idx = raw_output.find(end_marker, start_idx)

                    if end_idx != -1:
                        feedback = raw_output[start_idx:end_idx].strip()

                        if feedback == 'CANCELLED':
                            return ''

                        return feedback if feedback else 'No feedback provided by user'

            return raw_output if raw_output else 'No feedback provided by user'
        else:
            return f"Error running feedback UI: {result.stderr}"

    except Exception as e:
        return f"Error in human_in_the_loop tool: {str(e)}"


























# Register all tool categories
from tools.registrations import (
    register_github_tools,
    register_devops_tools,
    register_git_tools,
    register_observability_tools,
    register_rag_tools,
)



register_github_tools(mcp)
register_devops_tools(mcp)
register_git_tools(mcp)

register_observability_tools(mcp)
register_rag_tools(mcp)








async def main():
    await mcp.run_stdio_async()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
