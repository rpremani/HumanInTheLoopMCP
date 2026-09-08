# Human-in-the-Loop MCP Server — Complete Documentation

> **Version:** 1.2026.0317.2158  
> **Author:** CMART Solutions  
> **Last Updated:** June 2026

---

## Table of Contents

1. [What Is It?](#what-is-it)
2. [Why Does It Exist?](#why-does-it-exist)
3. [Who Is It For?](#who-is-it-for)
4. [How Does It Work?](#how-does-it-work)
5. [Architecture Diagram](#architecture-diagram)
6. [Component Breakdown](#component-breakdown)
7. [Tool Inventory (27 Tools)](#tool-inventory-27-tools)
8. [Installation & Setup](#installation--setup)
9. [Configuration](#configuration)
10. [Usage Scenarios](#usage-scenarios)
11. [Feedback UI — Desktop Application](#feedback-ui--desktop-application)
12. [Data Flow Diagram](#data-flow-diagram)
13. [File Structure](#file-structure)
14. [Build & Deployment](#build--deployment)
15. [Customization](#customization)
16. [Troubleshooting](#troubleshooting)
17. [FAQ](#faq)
18. [Roadmap](#roadmap)

---

## What Is It?

The **Human-in-the-Loop (HITL) MCP Server** is a [Model Context Protocol](https://modelcontextprotocol.io/) server that runs alongside AI coding agents (like GitHub Copilot in VS Code). It provides:

- A **structured checkpoint** where the AI pauses and asks a human for feedback before continuing
- A **desktop popup window** (WPF application) that displays what the AI has done and collects the user's response
- **27 integrated tools** for DevOps, GitHub, observability, and RAG workflows — all accessible to the AI agent through a single server

In one sentence: **It gives humans a voice inside AI-driven workflows — at the right moment, with the right context.**

---

## Why Does It Exist?

### The Core Problem

When AI agents work without checkpoints, three compounding failures occur:

```
┌──────────────────────────────────────────────────────┐
│                  THE GUESSING TRAP                     │
│                                                        │
│  Long conversation → Context lost → AI guesses →       │
│  Wrong output → Human corrects → Re-explains context → │
│  More tokens burned → Repeat                           │
│                                                        │
│  "AI burns your tokens because it's guessing —         │
│   this solution prevents it."                          │
└──────────────────────────────────────────────────────┘
```

### Problem Breakdown

| # | Problem | Impact | Who Suffers |
|---|---------|--------|-------------|
| 1 | **Context Loss** | AI's working memory degrades over long conversations. Early decisions, files, and constraints fall off the context window. | Developers, Non-developers |
| 2 | **Hallucination Under Uncertainty** | Without enough confirmed context, the AI fabricates plausible but incorrect answers, code, or actions. | Everyone |
| 3 | **Token Overrun from Correction Loops** | Every post-hoc correction re-explains context the model lost — consuming more tokens than the original task. | Budget owners, Developers |
| 4 | **Misaligned Output** | The AI completes a task perfectly — the WRONG task. Without mid-task validation, significant work is wasted. | Project leads, Developers |
| 5 | **No Handoff Point for Non-Technical Users** | Non-developers see results only at the end — too late to intercept drift. | Business users, QA |
| 6 | **Lack of Auditability** | No record of what the AI decided autonomously vs. what a human approved. | Compliance, Security teams |
| 7 | **Overcautious AI Behaviour** | Without a structured channel, AI either asks trivial questions constantly OR assumes silently — both are bad. | Everyone |
| 8 | **Developer-Tool Disconnect** | AI tools in VS Code are inaccessible to non-developers. | Business users |

### What HITL Changes

```
BEFORE (no checkpoint):
  AI starts → works → works → works → delivers output
                                         ↓
                              Human reviews → "That's wrong"
                                         ↓
                              Re-explain everything → more tokens

AFTER (with HITL checkpoint):
  AI starts → works → CHECKPOINT → human reviews mid-task
                                         ↓
                              "Looks good" or "Change X"
                                         ↓
                              AI continues with confirmed context
```

---

## Who Is It For?

### Primary Users

| Persona | How They Use HITL | What They Get |
|---------|-------------------|---------------|
| **Developers** | Configure once in VS Code. The AI agent calls `human_in_the_loop` when it needs validation. A popup appears — they read, type feedback, continue. | Fewer correction loops, confirmed context at every step, 27 integrated DevOps tools |
| **Non-Developers** (Business users, QA, Managers) | A popup window appears on their screen. They read the summary (in markdown), optionally click a suggested action button, and submit. No terminal, no code. | Visibility into AI progress, ability to steer without technical knowledge |
| **Team Leads / Architects** | Review the AI's proposed changes at key milestones before they're committed. | Oversight without micromanagement |
| **Security / Compliance** | The feedback checkpoint creates an auditable record of human-approved decisions. | Governance trail |

### Whose Workflow Does It Touch?

Anyone interacting with an AI agent in VS Code — or anyone who receives a feedback popup from an AI-driven process.

---

## How Does It Work?

### The 4-Step Flow

```
┌─────────────┐     ┌──────────────────┐     ┌───────────────────┐     ┌─────────────────┐
│  1. AI       │     │  2. Popup        │     │  3. Human         │     │  4. AI           │
│  reaches a   │────▸│  window opens    │────▸│  reads summary &  │────▸│  continues with  │
│  checkpoint  │     │  with summary    │     │  gives feedback   │     │  confirmed       │
│              │     │  + quick actions  │     │                   │     │  context         │
└─────────────┘     └──────────────────┘     └───────────────────┘     └─────────────────┘
```

### Technical Flow (Detailed)

```
VS Code + AI Agent (e.g. Copilot)
        │
        │ calls mcp tool: human_in_the_loop(summary, path, suggested_actions)
        │
        ▼
┌──────────────────────────────┐
│  HITL MCP Server (Python)    │
│  human-in-the-loop-mcp-      │
│  server.exe                  │
│                              │
│  Receives tool call via      │
│  MCP stdio protocol          │
└──────────┬───────────────────┘
           │
           │ subprocess.run(feedback-ui.exe, summary, path, [actions])
           │
           ▼
┌──────────────────────────────┐
│  Feedback UI (WPF / C#)     │
│  feedback-ui.exe             │
│                              │
│  ┌────────────────────────┐  │
│  │  CMART Solutions logo  │  │
│  ├────────────────────────┤  │
│  │  Markdown summary      │  │
│  │  (rendered with rich   │  │
│  │   formatting)          │  │
│  ├────────────────────────┤  │
│  │  Quick Action buttons  │  │
│  │  [Run tests] [Deploy]  │  │
│  ├────────────────────────┤  │
│  │  Feedback text box     │  │
│  │  [Submit] [Cancel]     │  │
│  └────────────────────────┘  │
└──────────┬───────────────────┘
           │
           │ stdout: MCP_RESPONSE_START{feedback}MCP_RESPONSE_END
           │
           ▼
┌──────────────────────────────┐
│  HITL MCP Server             │
│  Returns feedback string     │
│  to the AI agent             │
└──────────┬───────────────────┘
           │
           ▼
    AI Agent continues with
    human-confirmed context
```

### When Does the Popup Appear?

The AI agent decides when to call `human_in_the_loop`. Common trigger points:

- After completing a multi-step task (before moving on)
- Before destructive actions (deploy, delete, push)
- When the AI is uncertain about requirements
- At natural workflow milestones
- When the prompt `use_human_feedback` instructs it to

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          VS CODE                                 │
│                                                                   │
│  ┌──────────────┐     MCP (stdio)     ┌────────────────────┐    │
│  │  AI Agent     │◄──────────────────▸│  HITL MCP Server   │    │
│  │  (Copilot)    │                     │  (Python, PyInst.) │    │
│  └──────────────┘                     │                    │    │
│                                        │  27 Tools:         │    │
│                                        │  ├─ human_in_loop  │    │
│                                        │  ├─ github_*       │    │
│                                        │  ├─ openshift_*    │    │
│                                        │  ├─ harness_*      │    │
│                                        │  ├─ splunk_*       │    │
│                                        │  ├─ rag_*          │    │
│                                        │  └─ git_*          │    │
│                                        └─────────┬──────────┘    │
│                                                   │               │
└───────────────────────────────────────────────────┼───────────────┘
                                                    │
                                          subprocess │
                                                    ▼
                                        ┌────────────────────┐
                                        │  Feedback UI       │
                                        │  (WPF / .NET 8)    │
                                        │  Desktop Popup     │
                                        └────────────────────┘
                                                    │
                                    ┌───────────────┼───────────────┐
                                    │               │               │
                                    ▼               ▼               ▼
                               ┌────────┐    ┌──────────┐    ┌──────────┐
                               │ GitHub │    │ OpenShift│    │ Splunk   │
                               │ API    │    │ Cluster  │    │ Instance │
                               └────────┘    └──────────┘    └──────────┘
                                    │
                                    ├──▸ Harness (CI/CD)
                                    ├──▸ ChromaDB (RAG)
                                    └──▸ Git (local)
```

---

## Component Breakdown

### 1. MCP Server (`human-in-the-loop-mcp-server.exe`)

| Property | Value |
|----------|-------|
| Language | Python 3.11 |
| Framework | FastMCP (`mcp.server.fastmcp`) |
| Packaging | PyInstaller (single-file `.exe`) |
| Protocol | MCP over stdio |
| Size | ~100 MB |
| Dependencies | mcp 1.26.0, pydantic 2.12.5, chromadb 1.5.5, playwright 1.58.0, cryptography 46.0.5 |

**What it does:**
- Registers 27 tools + 1 prompt with the MCP protocol
- Listens on stdin/stdout for tool invocations from the AI agent
- When `human_in_the_loop` is called, launches `feedback-ui.exe` as a subprocess
- Routes other tool calls to appropriate clients (GitHub, OpenShift, Harness, Splunk, RAG)

### 2. Feedback UI (`feedback-ui.exe`)

| Property | Value |
|----------|-------|
| Language | C# |
| Framework | WPF (.NET 8, Windows Desktop) |
| Deployment | Self-contained (all .NET runtime DLLs included) |
| Size | ~151 KB exe + ~120 MB runtime DLLs |
| Theme | Forced dark mode, CMART red accent, white text |

**What it does:**
- Receives summary, project path, and suggested actions as command-line arguments
- Renders the summary as formatted markdown (headings, code blocks, lists, links)
- Displays clickable "Quick Action" buttons for common responses
- Supports file autocomplete (`@` trigger) from the project directory
- Returns user feedback via stdout with `MCP_RESPONSE_START` / `MCP_RESPONSE_END` markers

### 3. Tool Modules

```
tools/
├── registrations.py      # Registers all tool categories with the MCP server
├── github_pr.py          # PR review, file content, checks, comments
├── github_actions.py     # Workflow runs, triggers, job logs
├── git_operations.py     # Branch create, PR create, merge
├── harness.py            # Pipeline info, trigger deployment, wait, approval
├── openshift.py          # Deployment health, pod info, run oc commands
├── splunk.py             # Log search, trace search
└── rag.py                # Add document/folder, search, list, delete, stats
```

### 4. Utility Clients

```
utils/
├── github_client.py      # GitHub REST API wrapper (auth, rate limiting)
├── harness_client.py     # Harness API client (pipeline, execution, approval)
├── openshift_client.py   # OpenShift API client (deployments, pods, commands)
├── openshift_oauth.py    # OpenShift OAuth authentication flow
├── splunk_client.py      # Splunk REST API client (search, trace)
├── rag_client.py         # ChromaDB + embedding client for RAG operations
└── embedding_client.py   # Text embedding via OpenAI-compatible API
```

---

## Tool Inventory (27 Tools)

### Human Feedback (1 tool + 1 prompt)

| Tool | Description |
|------|-------------|
| `human_in_the_loop` | Opens desktop UI, shows summary + path, collects user feedback |
| `use_human_feedback` (prompt) | Instructions for when/how to invoke the feedback tool |

### GitHub Tools (7 tools)

| Tool | Description |
|------|-------------|
| `get_pr_for_review` | Fetch PR details (diff, description, metadata) |
| `get_pr_file_content` | Get specific file content from a PR |
| `get_pr_checks_status` | Get CI/CD check status for a PR |
| `add_pr_comment` | Add a comment to a pull request |
| `submit_pr_review` | Submit an approve/request-changes review |
| `get_workflow_runs` | List recent GitHub Actions workflow runs |
| `get_workflow_run_details` | Get detailed logs for a specific workflow run |
| `trigger_workflow` | Trigger a GitHub Actions workflow dispatch |

### Git Operations (3 tools)

| Tool | Description |
|------|-------------|
| `git_create_pr` | Create a new pull request |
| `merge_pr` | Merge a pull request |
| `create_branch` | Create a new branch (not registered — stub) |

### DevOps — OpenShift (4 tools)

| Tool | Description |
|------|-------------|
| `ocp_login` | Authenticate to an OpenShift cluster |
| `get_ocp_deployment` | Get deployment status and details |
| `get_ocp_pod_info` | Get pod info (status, logs, events) |
| `check_ocp_deployment_health` | Health check for a deployment |
| `run_oc_command` | Execute arbitrary `oc` CLI commands |

### DevOps — Harness (4 tools)

| Tool | Description |
|------|-------------|
| `get_harness_pipeline_info` | Get pipeline configuration and details |
| `trigger_harness_deployment` | Trigger a pipeline execution |
| `wait_for_harness_deployment` | Poll execution status until complete |
| `get_harness_execution_status` | Get current execution status |

### Observability — Splunk (2 tools)

| Tool | Description |
|------|-------------|
| `splunk_search` | Search Splunk logs with SPL queries |
| `splunk_trace_search` | Search distributed traces |

### RAG — Vector Search (5 tools)

| Tool | Description |
|------|-------------|
| `rag_add_document` | Index a document into ChromaDB |
| `rag_add_folder` | Index an entire folder recursively |
| `rag_search` | Semantic search across indexed documents |
| `rag_list_collections` | List all RAG collections |
| `rag_delete` | Delete a collection or document |
| `rag_get_stats` | Get collection statistics |

---

## Installation & Setup

### Prerequisites

| Requirement | Details |
|-------------|---------|
| **Operating System** | Windows 10 / 11 (x64) |
| **VS Code** | 1.90+ with MCP extension support |
| **AI Agent** | GitHub Copilot (or any MCP-compatible agent) |
| **No additional runtime** | Everything is self-contained in the executables |

### Step 1 — Download / Deploy

Copy the deployment folder containing:
```
deployment-folder/
├── human-in-the-loop-mcp-server.exe    ← MCP server (Python, ~100 MB)
├── feedback-ui.exe                      ← Feedback window (C#, ~151 KB)
├── feedback-ui.dll                      ← Core assembly
├── feedback-ui.deps.json
├── feedback-ui.runtimeconfig.json
├── Markdig.dll                          ← Markdown rendering library
├── coreclr.dll                          ← .NET 8 runtime
├── PresentationFramework.dll            ← WPF framework
├── ... (~250 more .NET runtime DLLs)
└── CMART.png                            ← Logo (embedded in assembly)
```

> **Critical:** `feedback-ui.exe` and `human-in-the-loop-mcp-server.exe` **must be in the same folder**. The server looks for the UI executable in its own directory.

### Step 2 — Configure VS Code

Open VS Code settings:
- `Ctrl+Shift+P` → "Preferences: Open User Settings (JSON)"
- Or create/edit `.vscode/mcp.json` in your workspace

Add or update the MCP server entry:

```json
{
  "mcp": {
    "servers": {
      "Human-In-The-Loop-MCP": {
        "type": "stdio",
        "command": "C:\\path\\to\\deployment-folder\\human-in-the-loop-mcp-server.exe",
        "args": []
      }
    }
  }
}
```

Or in workspace-level `.vscode/mcp.json`:

```json
{
  "servers": {
    "Human-In-The-Loop-MCP": {
      "type": "stdio",
      "command": "C:\\path\\to\\deployment-folder\\human-in-the-loop-mcp-server.exe",
      "args": []
    }
  }
}
```

### Step 3 — Verify

1. Restart VS Code (or reload the MCP extension)
2. Open Copilot Chat
3. The AI agent should now have access to 27 tools including `human_in_the_loop`
4. Ask the agent to call `human_in_the_loop` — a popup should appear

### Step 4 — Environment Variables (Optional)

For tools beyond the feedback loop, set these environment variables or use a `.env` file alongside the server:

| Variable | Purpose | Required For |
|----------|---------|--------------|
| `GITHUB_TOKEN` | GitHub personal access token | GitHub tools |
| `HARNESS_API_KEY` | Harness API key | Harness tools |
| `HARNESS_ACCOUNT_ID` | Harness account identifier | Harness tools |
| `OCP_SERVER_URL` | OpenShift cluster URL | OpenShift tools |
| `OCP_TOKEN` | OpenShift auth token | OpenShift tools |
| `SPLUNK_HOST` | Splunk instance URL | Splunk tools |
| `SPLUNK_TOKEN` | Splunk HEC token | Splunk tools |
| `EMBEDDING_API_URL` | Embedding model endpoint | RAG tools |
| `EMBEDDING_API_KEY` | Embedding API key | RAG tools |

---

## Configuration

### MCP Server Configuration

The server reads configuration from environment variables and `.env` files. Place a `.env` file in the same directory as the server executable.

### Feedback UI Behaviour

| Behaviour | How It Works |
|-----------|-------------|
| **Suggested Actions** | Pass a list of strings as the third argument. They appear as clickable pill buttons. |
| **File Autocomplete** | Type `@` in the feedback text box to trigger file path autocomplete from the project directory |
| **Markdown Rendering** | The summary supports full markdown: headings, bold, code blocks, lists, links |
| **Cancel** | Clicking Cancel or closing the window returns `CANCELLED` (treated as empty feedback) |
| **Submit** | Clicking Submit or pressing `Ctrl+Enter` returns the feedback text |

---

## Usage Scenarios

### Scenario 1: Developer — Code Review Assistance

```
Developer: "Review PR #42 and suggest improvements"

AI Agent:
  1. Calls get_pr_for_review(owner, repo, 42)
  2. Analyzes diff, identifies issues
  3. Calls human_in_the_loop(
       summary="## PR #42 Review\n\nFound 3 issues:\n1. Missing null check...",
       path="c:/projects/my-app",
       suggested_actions=["Submit review as-is", "Add more detail", "Skip this PR"]
     )
  4. Popup appears → Developer reads → Types "Also check the test coverage"
  5. AI continues with developer's additional direction
```

### Scenario 2: Non-Developer — Deployment Approval

```
Manager: "Deploy the latest build to staging"

AI Agent:
  1. Calls trigger_harness_deployment(pipeline, stage)
  2. Calls wait_for_harness_deployment(execution_id)
  3. Pipeline requires approval
  4. Calls human_in_the_loop(
       summary="## Deployment to Staging\n\n✅ Build passed\n✅ Tests green\n⏳ Awaiting approval",
       path="c:/projects/my-app",
       suggested_actions=["Approve deployment", "Reject - needs more testing", "Check logs first"]
     )
  5. Popup appears → Manager clicks "Approve deployment"
  6. AI proceeds with approval
```

### Scenario 3: Multi-Step Task with Checkpoints

```
Developer: "Refactor the auth module and add tests"

AI Agent:
  1. Reads existing auth module
  2. Plans 4 changes
  3. Makes changes 1 & 2
  4. Calls human_in_the_loop(
       summary="## Auth Refactor Progress\n\n### Done:\n- Extracted JWT validation\n- Added token refresh\n\n### Next:\n- Update error handling\n- Add unit tests",
       path="c:/projects/my-app",
       suggested_actions=["Continue", "Undo last change", "Show me the code so far"]
     )
  5. Developer reviews → "Continue, but use mock tokens in tests"
  6. AI continues with confirmed direction + new requirement
```

---

## Feedback UI — Desktop Application

### Window Layout

```
┌─────────────────────────────────────────────────────┐
│  [CMART Solutions Logo]                              │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ╔════════════════════════════════════════════════╗  │
│  ║  ## Summary Title                    [Copy 📋] ║  │
│  ║                                                ║  │
│  ║  Rendered markdown content...                  ║  │
│  ║  - Bullet points                               ║  │
│  ║  - **Bold text**                               ║  │
│  ║  - `code blocks`                               ║  │
│  ║  - Links                                       ║  │
│  ╚════════════════════════════════════════════════╝  │
│                                                      │
│  Quick Actions:                                      │
│  [Run tests] [Deploy to staging] [Review changes]    │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  Type your feedback here...                     │  │
│  │  (supports @file autocomplete)                  │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  [Cancel]                              [Submit ✓]    │
│                                                      │
│  Version 1.2026.0317.2158                            │
└─────────────────────────────────────────────────────┘
```

### Theme

| Element | Value |
|---------|-------|
| Background | `#2B2B2B` (charcoal grey) |
| Text | `#F0F0F0` (white) |
| Accent (buttons, links) | `#ED4040` (CMART red) |
| Hover | `#C83232` (darker red) |
| Text input area | `#373737` (slightly lighter grey) |
| Secondary text | `#AAAAAA` (mid grey) |
| Code blocks | `#161B22` background, `#C9D1D9` text |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Submit feedback |
| `Escape` | Cancel / Close |
| `@` | Trigger file autocomplete |
| `Arrow keys` | Navigate autocomplete list |
| `Tab` / `Enter` | Select autocomplete item |

---

## Data Flow Diagram

```
                    ┌──────────────────┐
                    │   User (Human)    │
                    └────────┬─────────┘
                             │ reads summary, types feedback
                             ▼
┌───────────┐     ┌──────────────────┐     ┌───────────────────┐
│ VS Code / │     │  Feedback UI     │     │  MCP Server       │
│ AI Agent  │◄───▸│  (WPF Desktop)   │◄───▸│  (Python Server)  │
│           │     │                  │     │                   │
│ Sends     │     │ Renders markdown │     │ Receives tool     │
│ tool call │     │ Shows actions    │     │ call via stdio    │
│ via MCP   │     │ Collects input   │     │ Launches UI exe   │
└───────────┘     └──────────────────┘     │ Returns feedback  │
                                            │                   │
                                            │ Also routes to:   │
                                            │ ├─ GitHub API     │
                                            │ ├─ OpenShift API  │
                                            │ ├─ Harness API    │
                                            │ ├─ Splunk API     │
                                            │ └─ ChromaDB (RAG) │
                                            └───────────────────┘
```

### Communication Protocol

```
VS Code  ──stdin──▸  MCP Server  ──subprocess──▸  Feedback UI
         ◂─stdout──              ◂───stdout─────

Messages are JSON-RPC 2.0 over stdio (MCP standard).
Feedback UI uses stdout markers:
  MCP_RESPONSE_START<feedback text>MCP_RESPONSE_END
```

---

## File Structure

```
deployment-folder/
│
├── human-in-the-loop-mcp-server.exe     # Main server executable
│   └── (embedded Python 3.11 + all dependencies)
│       ├── server.py                     # Entry point
│       ├── tools/
│       │   ├── registrations.py          # Tool registration
│       │   ├── github_pr.py
│       │   ├── github_actions.py
│       │   ├── git_operations.py
│       │   ├── harness.py
│       │   ├── openshift.py
│       │   ├── splunk.py
│       │   └── rag.py
│       └── utils/
│           ├── github_client.py
│           ├── harness_client.py
│           ├── openshift_client.py
│           ├── openshift_oauth.py
│           ├── splunk_client.py
│           ├── rag_client.py
│           └── embedding_client.py
│
├── feedback-ui.exe                       # Feedback window executable
├── feedback-ui.dll                       # Core C# assembly
├── feedback-ui.deps.json
├── feedback-ui.runtimeconfig.json
├── Markdig.dll                           # Markdown rendering
├── coreclr.dll                           # .NET 8 runtime
├── PresentationFramework.dll             # WPF
├── ... (~250 more .NET DLLs)
└── .env (optional)                       # Environment variables
```

### Source Code Structure

```
decompiled-source/
├── server-source-final/
│   ├── server.py                         # Main MCP server
│   ├── tools/                            # Tool implementations
│   ├── utils/                            # API clients
│   ├── requirements.txt                  # Python dependencies (pinned)
│   ├── human-in-the-loop-mcp-server.spec # PyInstaller build spec
│   └── dist/                             # Built deployment folder
│
├── feedback-ui/
│   ├── feedback-ui.csproj                # WPF project file
│   ├── feedback_ui/
│   │   ├── App.cs                        # Application entry point
│   │   ├── MainWindow.cs                 # Main window (1530 lines)
│   │   ├── MarkdownConverter.cs          # Markdown → FlowDocument
│   │   ├── ThemeDetector.cs              # OS theme detection
│   │   └── WindowHelper.cs              # Window helper (dark title bar)
│   ├── Properties/
│   │   └── AssemblyInfo.cs              # Version info
│   ├── mainwindow.baml                   # Compiled XAML layout
│   ├── CMART.png                         # Logo
│   ├── user-check-light.png              # App icon (light)
│   ├── user-check-dark.png               # App icon (dark)
│   └── publish-output/                   # Self-contained deployment
│
└── HITL_MCP_Server_Documentation.md      # This file
```

---

## Build & Deployment

### Building the MCP Server (Python)

```powershell
cd server-source-final

# Create virtual environment
uv venv .venv --python 3.11

# Activate
.venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Build single-file executable
python -m PyInstaller human-in-the-loop-mcp-server.spec --clean

# Output: dist/human-in-the-loop-mcp-server.exe
```

### Building the Feedback UI (C#)

```powershell
cd feedback-ui

# Build framework-dependent (for development)
dotnet build -c Release

# Publish self-contained (for deployment)
dotnet publish -c Release -r win-x64 --self-contained true -o publish-output

# Output: publish-output/feedback-ui.exe + runtime DLLs
```

### Creating a Deployment Package

```powershell
# Create deployment folder
New-Item -ItemType Directory "C:\mcp-deploy" -Force

# Copy MCP server
Copy-Item "server-source-final\dist\human-in-the-loop-mcp-server.exe" "C:\mcp-deploy\"

# Copy all feedback-ui files (self-contained)
Copy-Item "feedback-ui\publish-output\*" "C:\mcp-deploy\" -Recurse
```

---

## Customization

### Changing the Branding

**Logo:** Replace `CMART.png` in the `feedback-ui/` directory, rebuild, and republish.

**Logo code** in `MainWindow.cs` → `AddBrandingHeader()`:
```csharp
var logo = new Image
{
    Source = new BitmapImage(new Uri("pack://application:,,,/CMART.png")),
    Height = 36,    // ← adjust size here
    Stretch = Stretch.Uniform,
    HorizontalAlignment = HorizontalAlignment.Center,
    Margin = new Thickness(0, 6, 0, 2)  // ← adjust spacing here
};
```

### Changing the Theme Colors

In `MainWindow.cs` → `ApplyDarkTheme()`:
```csharp
Resources["BackgroundBrush"]  = new SolidColorBrush(Color.FromRgb(43, 43, 43));    // Window bg
Resources["AccentBrush"]      = new SolidColorBrush(Color.FromRgb(237, 64, 64));   // Button/link color
Resources["HoverBrush"]       = new SolidColorBrush(Color.FromRgb(200, 50, 50));   // Button hover
Resources["ForegroundBrush"]  = new SolidColorBrush(Color.FromRgb(240, 240, 240)); // Main text
Resources["TextBoxBrush"]     = new SolidColorBrush(Color.FromRgb(55, 55, 55));    // Input area bg
Resources["BorderBrush"]      = new SolidColorBrush(Color.FromRgb(70, 70, 70));    // Border lines
Resources["SecondaryBrush"]   = new SolidColorBrush(Color.FromRgb(170, 170, 170)); // Secondary text
```

### Adding New Tools

1. Create a new Python file in `tools/` (e.g., `tools/my_tool.py`)
2. Define async functions decorated with `@mcp.tool(...)`
3. Register in `tools/registrations.py`:
   ```python
   def register_my_tools(mcp):
       from tools.my_tool import *
   ```
4. Call from `server.py`:
   ```python
   from tools.registrations import register_my_tools
   register_my_tools(mcp)
   ```
5. Rebuild with PyInstaller

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Popup doesn't appear | `feedback-ui.exe` not in same folder as server | Move both executables to the same directory |
| Black text on dark background | Theme not applied to markdown content | Rebuild with latest code (forced dark theming) |
| "Tool not found" in VS Code | MCP server not configured or not running | Check `settings.json` path, restart VS Code |
| Server crashes on startup | Missing environment variables for some tools | Set required env vars or use `.env` file |
| Feedback UI shows error | .NET runtime not found (framework-dependent build) | Use self-contained publish (`--self-contained true`) |
| Large exe size (~100 MB) | PyInstaller bundles Python + all dependencies | Normal — includes chromadb, numpy, playwright, etc. |

---

## FAQ

**Q: Does it need internet access?**  
A: The feedback popup itself works fully offline. Individual tools (GitHub, OpenShift, etc.) need network access to their respective APIs.

**Q: Can I use it on macOS or Linux?**  
A: The MCP server (Python) is cross-platform. The feedback UI (WPF) is Windows-only. A cross-platform UI (Electron/web) is on the roadmap.

**Q: Does it store my feedback anywhere?**  
A: No. Feedback is passed directly from the UI to the MCP server to the AI agent. Nothing is persisted to disk.

**Q: Can I use it without VS Code?**  
A: Yes, any MCP-compatible client can connect to the server. VS Code is the primary supported environment.

**Q: How many tools are disabled?**  
A: 4 tools (Checkmarx-related) are disabled in the current build. 27 are active.

**Q: Can non-developers install it themselves?**  
A: Non-developers don't install anything. They just see the popup when an AI workflow reaches a checkpoint. Developers configure the server in VS Code.

---

## Roadmap

### Near-Term (Weeks 1–6)

| Phase | Timeline | Activities |
|-------|----------|------------|
| **POC** | Week 1–2 | Install with 3–5 pilot developers. Gather first-use feedback. Verify integration. |
| **Refinement** | Week 3–4 | UI tweaks from pilot feedback. Onboarding guide for non-developers. Edge-case testing. |
| **Broader Rollout** | Week 5–6 | Roll out to wider developer team. Share with non-technical stakeholders. Measure patterns. |

### Medium-Term

- Quantified token usage comparison (with vs. without HITL)
- Cross-platform feedback UI (Electron or web-based)
- Feedback history / audit log
- Team-level analytics dashboard
- Integration with Jira / ServiceNow for approval workflows

### Long-Term Vision

- Self-learning checkpoints (AI learns WHEN to ask based on past feedback)
- Multi-user approval chains (design review → security → deploy)
- Natural language policy rules ("always ask before deleting files")

---

*© CMART Solutions 2025. All rights reserved.*
