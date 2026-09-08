# Human-in-the-Loop MCP Server

> **Version:** 1.2026.0317.2158 &nbsp;|&nbsp; **Author:** CMART Solutions &nbsp;|&nbsp; **Platform:** Windows x64

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that gives humans a structured voice inside AI-driven workflows — at the right moment, with the right context.

When an AI agent (e.g. GitHub Copilot) calls the `human_in_the_loop` tool, a native WPF desktop popup appears, displays a Markdown summary of what the AI has done, and waits for the user's feedback before continuing.

---

## Features

- **Desktop feedback popup** — WPF application with Markdown rendering and quick-action buttons
- **27 integrated MCP tools** across GitHub, Harness CI/CD, OpenShift, Splunk, and RAG
- **Self-contained executables** — no Python or .NET runtime required on the target machine
- **Prompt template** (`use_human_feedback`) — instructs the AI agent to use HITL checkpoints automatically

---

## Architecture

```
VS Code (GitHub Copilot)
        │  MCP stdio
        ▼
human-in-the-loop-mcp-server.exe   ← PyInstaller bundle (Python MCP server)
        │  subprocess
        ▼
feedback-ui.exe                    ← Self-contained WPF app (.NET 8, win-x64)
        │  stdout
        ▼
User feedback string returned to AI agent
```

---

## Repository Structure

```
├── server-source-final/        # MCP server source (Python)
│   ├── server.py               # Entry point — FastMCP server with all tool registrations
│   ├── requirements.txt        # Python dependencies
│   ├── overrides.txt           # Pinned transitive dependency overrides
│   ├── tools/                  # Tool implementations
│   │   ├── git_operations.py
│   │   ├── github_actions.py
│   │   ├── github_pr.py
│   │   ├── harness.py
│   │   ├── openshift.py
│   │   ├── rag.py
│   │   ├── splunk.py
│   │   └── registrations/      # Tool registration modules per domain
│   └── utils/                  # API client helpers
│       ├── github_client.py
│       ├── harness_client.py
│       ├── openshift_client.py
│       ├── splunk_client.py
│       ├── rag_client.py
│       └── embedding_client.py
├── feedback-ui/                # WPF desktop popup source (C# / .NET 8)
│   ├── feedback-ui.csproj
│   ├── feedback_ui/            # Application source files
│   └── Properties/
├── tools/                      # Standalone utility scripts
├── HITL_MCP_Server_Documentation.md  # Full documentation
└── .env.example                # Environment variable template
```

---

## Quick Start (Target Machine)

### 1. Download the release

Download the latest release from [GitHub Releases](https://github.com/premanir/HumanInTheLoop/releases) and extract it to a folder, e.g. `C:\Tools\hitl\`.

The release contains two self-contained executables — no installation required:
- `human-in-the-loop-mcp-server.exe` — the MCP server
- `feedback-ui.exe` — the WPF popup

### 2. Configure environment variables

Create a `.env` file next to `human-in-the-loop-mcp-server.exe` based on [.env.example](.env.example).  
Only configure the tools you intend to use — all variables are optional.

### 3. Add to VS Code `mcp.json`

Open `%APPDATA%\Code\User\mcp.json` and add:

```json
{
  "servers": {
    "Human-In-The-Loop": {
      "type": "stdio",
      "command": "C:\\Tools\\hitl\\human-in-the-loop-mcp-server.exe",
      "args": []
    }
  }
}
```

### 4. Restart VS Code

The MCP server starts automatically when needed. No further setup required.

---

## Building from Source

### MCP Server (Python → EXE)

```bash
cd server-source-final
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller human-in-the-loop-mcp-server.spec
```

Output: `dist\human-in-the-loop-mcp-server.exe`

### Feedback UI (C# → EXE)

```bash
cd feedback-ui
dotnet publish -c Release -r win-x64 --self-contained true
```

Output: `bin\Release\net8.0-windows\win-x64\publish\feedback-ui.exe`

Copy both executables into the same directory for deployment.

---

## Environment Variables

See [.env.example](.env.example) for all available configuration variables.

| Group | Variables |
|-------|-----------|
| GitHub | `GITHUB_TOKEN`, `GITHUB_API_URL` |
| Harness | `HARNESS_API_KEY`, `HARNESS_ACCOUNT_ID`, `HARNESS_ORG_ID`, `HARNESS_PROJECT_ID`, `HARNESS_PIPELINE_ID`, `HARNESS_API_URL`, `HARNESS_UI_BASE_URL` |
| OpenShift | `OPENSHIFT_API_URL`, `OPENSHIFT_CONSOLE_URL`, `OPENSHIFT_USERNAME`, `OPENSHIFT_PASSWORD`, `OPENSHIFT_TOKEN`, `OPENSHIFT_HEADLESS` |
| Splunk | `SPLUNK_URL`, `SPLUNK_TOKEN`, `SPLUNK_USERNAME`, `SPLUNK_PASSWORD` |
| Network | `HTTP_PROXY`, `HTTPS_PROXY` |

---

## Documentation

See [HITL_MCP_Server_Documentation.md](HITL_MCP_Server_Documentation.md) for full architecture, tool inventory, usage scenarios, and troubleshooting.

---

## License

&copy; CMART Solutions. All rights reserved.
