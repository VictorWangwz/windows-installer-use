# windows-installer-use

An LLM-powered agent that automatically clicks through Windows installer GUIs. Give it an `.exe`, it drives the installer to completion — no human required.

Built for security research: run installers in an isolated, snapshotted Windows VM and let the agent handle all the clicking while your analysis tools observe what happens.

## How It Works

1. Launches the `.exe` installer via `subprocess`
2. At each step, reads the installer's UI accessibility tree via **pywinauto** (Windows UIA)
3. If the accessibility tree is empty (non-standard UI framework), falls back to **LLM vision** — takes a screenshot and asks the model to identify clickable elements
4. Clicks through buttons in priority order: `Finish > Next > Accept > Agree > Install > Yes > OK > Continue`
5. Never clicks `Cancel`, `Decline`, `No`, `Quit`, `Exit`, or `Uninstall`
6. Stops when the installer closes after a "Finish" click

The LLM layer uses [LiteLLM](https://github.com/BerriAI/litellm) via LangChain — swap providers by changing a single env var.

## Quick Start

### Prerequisites

- Windows (pywinauto is Windows-only)
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Install

```bash
git clone https://github.com/VictorWangwz/windows-installer-use.git
cd windows-installer-use
uv sync
```

### Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
MODEL=anthropic:claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
MAX_STEPS=30
```

### Run

```bash
uv run python main.py --installer "C:\Users\you\Downloads\SomeInstaller.exe"
```

The installer window will appear on screen. Watch the agent click through it automatically.

## Configuration

| Variable | Description | Default |
|---|---|---|
| `MODEL` | LangChain model string (see below) | `anthropic:claude-sonnet-4-6` |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `MAX_STEPS` | Max tool-call steps before giving up | `30` |

### Supported Providers

Any model supported by LangChain's `init_chat_model`:

```env
# Anthropic
MODEL=anthropic:claude-sonnet-4-6

# OpenAI
MODEL=openai:gpt-4o
OPENAI_API_KEY=sk-...
```

## Architecture

```
main.py                        CLI entry point
└── agent/agent.py             LangGraph agent via create_agent()
        ├── agent/prompts.py   System prompt (button priorities, rules)
        └── agent/tools/
                ├── ui_tree.py     get_ui_tree  — pywinauto accessibility tree
                │                               → LLM vision fallback
                ├── click.py       click_element — pywinauto label click
                │                               → pyautogui coordinate fallback
                ├── type_text.py   type_text    — keyboard input for text fields
                └── wait.py        wait         — sleep N seconds
```

### UI Perception: Two-Tier Approach

**Tier 1 — Accessibility tree (pywinauto UIA)**
Reads button labels and positions directly from Windows without any API cost. Works on most modern installers (NSIS, Inno Setup, WiX, InstallShield).

**Tier 2 — LLM vision fallback**
If the accessibility tree is empty (e.g. custom Electron-based installers), captures a screenshot, encodes it as base64, and calls the LLM's vision API to identify interactive elements. Returns the same `{type, label, x, y}` format as tier 1 so the agent's decision loop is unchanged.

## Security Research Usage

This tool is designed to run inside an **isolated, snapshotted Windows VM**:

```
┌─────────────────────────────────────┐
│  Host machine                       │
│  ┌───────────────────────────────┐  │
│  │  Windows VM (isolated)        │  │
│  │  - Snapshot before each run   │  │
│  │  - No network to host         │  │
│  │  - Your analysis tools        │  │
│  │    (file monitor, registry    │  │
│  │     monitor, network capture) │  │
│  │  - windows-installer-use      │  │
│  │    clicks through the target  │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

**Workflow:**
1. Take a VM snapshot (clean state)
2. Copy the target `.exe` into the VM
3. Run `windows-installer-use` — it clicks through the installer
4. Your analysis tools capture what the installer does (file writes, registry changes, network calls, process spawns)
5. Revert VM to snapshot for the next sample

> **Note:** UAC prompts that require a password are not handled. Configure the VM to auto-approve UAC elevation for the test user.

## Development

```bash
# Run tests
uv run pytest -v

# Run a single test file
uv run pytest tests/tools/test_ui_tree.py -v
```

18 tests covering all tools, the agent factory, and the CLI entry point.

## License

MIT
