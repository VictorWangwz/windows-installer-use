# Windows Installer Automation Agent — Design Spec

**Date:** 2026-05-27  
**Status:** Approved

---

## Overview

A Python CLI tool that takes a Windows `.exe` installer as input, launches it visibly on screen, and runs a LangChain agent loop that automatically clicks through the installer GUI until installation completes. Designed to run inside an isolated, snapshotted Windows VM for security research purposes.

---

## Architecture

```
CLI entry point (main.py)
    └── InstallerAgent (LangChain AgentExecutor)
            ├── Tool: get_ui_tree       ← pywinauto accessibility tree (primary)
            ├── Tool: take_screenshot   ← Pillow/mss screenshot → base64 (fallback)
            ├── Tool: click_element     ← pywinauto or pyautogui coordinate click
            ├── Tool: type_text         ← keyboard input for text fields
            └── Tool: wait              ← pause for installer animations/loading
```

**Control flow:**
1. Launch the `.exe` via `subprocess`
2. Agent loop: get state → LLM decides action → execute tool → repeat
3. Agent detects completion when no installer windows remain or a "Finish" button was clicked
4. Exit and print a summary of steps taken

**LLM layer:** `LiteLLM` via LangChain's `ChatLiteLLM`. Swap providers by changing one env var — no code changes needed.

---

## Tools

### `get_ui_tree`
- **What it does:** Uses `pywinauto` to walk the accessibility tree of the foreground installer window. Returns a structured list of interactive elements (buttons, checkboxes, text fields, radio buttons) with their labels and screen positions.
- **When used:** Every step, as the primary perception method.
- **Returns `None`:** If the window isn't accessible or exposes no controls.

### `take_screenshot`
- **What it does:** Captures the full screen using `mss`, encodes as base64 PNG, returns it for LLM vision analysis.
- **When used:** Fallback when `get_ui_tree` returns empty or ambiguous results. Also used when the agent needs visual confirmation before acting.

### `click_element`
- **What it does:** Clicks a UI control. Accepts either a `pywinauto` control reference (from UI tree) or `(x, y)` screen coordinates (from vision fallback). Tries `pywinauto` click first, falls back to `pyautogui` coordinate click.

### `type_text`
- **What it does:** Types a string into the currently focused field. Used for installer prompts asking for install path, license key, username, etc.

### `wait`
- **What it does:** Sleeps N seconds (default: 2). Used after clicking "Install" while a progress bar runs, or after any action that triggers a screen transition.

---

## Agent Prompt Strategy

The system prompt instructs the agent to:
- Always call `get_ui_tree` first; only call `take_screenshot` if the tree is empty or ambiguous
- Prefer clicking buttons in this priority order: **Finish > Next > Accept/Agree > Install > Yes > OK**
- Never click **Cancel**, **Decline**, **No**, or **Exit**
- Call `wait` after any click that triggers a loading screen or progress bar
- Declare the task done when no installer window is detected after a "Finish" click
- Give up and report failure after `MAX_STEPS` iterations

---

## Project Structure

```
windows-use/
├── agent/
│   ├── __init__.py
│   ├── agent.py          ← LangChain AgentExecutor setup + main loop
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── ui_tree.py    ← get_ui_tree tool
│   │   ├── screenshot.py ← take_screenshot tool
│   │   ├── click.py      ← click_element tool
│   │   ├── type_text.py  ← type_text tool
│   │   └── wait.py       ← wait tool
│   └── prompts.py        ← system prompt template
├── main.py               ← CLI entry point (argparse)
├── pyproject.toml        ← dependencies managed with uv
└── .env.example          ← MODEL, API keys template
```

---

## Configuration

All config via environment variables (`.env` file):

| Variable | Description | Example |
|---|---|---|
| `MODEL` | LiteLLM model string | `claude-sonnet-4-6`, `gpt-4o` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `MAX_STEPS` | Max agent iterations before giving up | `30` |

---

## CLI Usage

```bash
python main.py --installer "C:\Users\wangz\Downloads\ZoomInstallerFull.exe"
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `langchain` | Agent framework and tool abstraction |
| `langchain-community` | ChatLiteLLM integration |
| `litellm` | Multi-provider LLM abstraction |
| `pywinauto` | Windows UI Automation (accessibility tree) |
| `pyautogui` | Coordinate-based mouse click fallback |
| `mss` | Fast cross-platform screenshot capture |
| `Pillow` | Image encoding for vision payloads |
| `python-dotenv` | `.env` file loading |

Managed with `uv` via `pyproject.toml`.

---

## Constraints & Assumptions

- Runs on Windows only (pywinauto is Windows-specific)
- The installer must create a visible GUI window (no silent/headless installers)
- The VM has network access to the chosen LLM provider's API
- The agent does not handle UAC prompts that require a password — the VM should be configured to auto-approve UAC
