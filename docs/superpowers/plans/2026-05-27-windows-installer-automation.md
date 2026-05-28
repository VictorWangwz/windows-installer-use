# Windows Installer Automation Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a LangChain agent that launches a Windows `.exe` installer and automatically clicks through its GUI until installation completes, using Windows UI Automation first and LLM vision as fallback.

**Architecture:** A `create_tool_calling_agent` + `AgentExecutor` loop drives five tools — `get_ui_tree` (pywinauto + vision fallback), `click_element`, `type_text`, and `wait`. The model is configured via `LiteLLM` so any provider can be used by setting a single env var.

**Tech Stack:** Python 3.11+, uv, LangChain 0.3+, langchain-community, LiteLLM, pywinauto, pyautogui, mss, Pillow, pytest, pytest-mock

---

## File Map

| File | Responsibility |
|---|---|
| `pyproject.toml` | Project deps and build config (uv) |
| `.env.example` | Env var template |
| `agent/__init__.py` | Package marker |
| `agent/prompts.py` | System prompt string |
| `agent/tools/__init__.py` | `build_tools(model)` factory |
| `agent/tools/wait.py` | `wait` tool — sleeps N seconds |
| `agent/tools/ui_tree.py` | `make_get_ui_tree(model)` — pywinauto + vision fallback |
| `agent/tools/click.py` | `click_element` tool — label or coordinate click |
| `agent/tools/type_text.py` | `type_text` tool — keyboard input |
| `agent/agent.py` | `build_agent()` — constructs AgentExecutor |
| `main.py` | CLI entry point |
| `tests/__init__.py` | Package marker |
| `tests/tools/__init__.py` | Package marker |
| `tests/tools/test_wait.py` | Tests for wait tool |
| `tests/tools/test_ui_tree.py` | Tests for get_ui_tree tool |
| `tests/tools/test_click.py` | Tests for click_element tool |
| `tests/tools/test_type_text.py` | Tests for type_text tool |
| `tests/test_agent.py` | Tests for build_agent |
| `tests/test_main.py` | Tests for CLI entry point |

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `agent/__init__.py`
- Create: `agent/tools/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/tools/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "windows-use"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "langchain>=0.3.0",
    "langchain-community>=0.3.0",
    "litellm>=1.50.0",
    "pywinauto>=0.6.8",
    "pyautogui>=0.9.54",
    "mss>=9.0.0",
    "Pillow>=10.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-mock>=3.14.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 2: Create `.env.example`**

```
MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
MAX_STEPS=30
```

- [ ] **Step 3: Create empty package markers**

```bash
touch agent/__init__.py agent/tools/__init__.py tests/__init__.py tests/tools/__init__.py
```

- [ ] **Step 4: Install dependencies**

```bash
uv sync --extra dev
```

Expected: no errors, `.venv` created.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example agent/__init__.py agent/tools/__init__.py tests/__init__.py tests/tools/__init__.py
git commit -m "chore: scaffold project with dependencies"
```

---

## Task 2: `wait` Tool

**Files:**
- Create: `agent/tools/wait.py`
- Create: `tests/tools/test_wait.py`

- [ ] **Step 1: Write failing tests**

`tests/tools/test_wait.py`:
```python
from unittest.mock import patch
from agent.tools.wait import wait


def test_wait_default_seconds():
    with patch("agent.tools.wait.time.sleep") as mock_sleep:
        result = wait.invoke({"seconds": 2})
        mock_sleep.assert_called_once_with(2)
        assert "2" in result


def test_wait_custom_seconds():
    with patch("agent.tools.wait.time.sleep") as mock_sleep:
        result = wait.invoke({"seconds": 10})
        mock_sleep.assert_called_once_with(10)
        assert "10" in result
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/tools/test_wait.py -v
```

Expected: `ModuleNotFoundError: No module named 'agent.tools.wait'`

- [ ] **Step 3: Implement `agent/tools/wait.py`**

```python
import time
from langchain_core.tools import tool


@tool
def wait(seconds: int = 2) -> str:
    """Wait for the specified number of seconds. Use after clicking Install or any action that triggers a loading screen or progress bar."""
    time.sleep(seconds)
    return f"Waited {seconds} seconds."
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/tools/test_wait.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/tools/wait.py tests/tools/test_wait.py
git commit -m "feat: add wait tool"
```

---

## Task 3: `get_ui_tree` Tool

**Files:**
- Create: `agent/tools/ui_tree.py`
- Create: `tests/tools/test_ui_tree.py`

- [ ] **Step 1: Write failing tests**

`tests/tools/test_ui_tree.py`:
```python
import json
from unittest.mock import patch, MagicMock, call
from agent.tools.ui_tree import make_get_ui_tree


def _make_mock_control(ctrl_type: str, label: str, left=100, right=200, top=50, bottom=80):
    ctrl = MagicMock()
    ctrl.element_info.control_type = ctrl_type
    ctrl.window_text.return_value = label
    rect = MagicMock()
    rect.left = left
    rect.right = right
    rect.top = top
    rect.bottom = bottom
    ctrl.rectangle.return_value = rect
    return ctrl


def test_returns_button_from_ui_automation():
    mock_ctrl = _make_mock_control("Button", "Next")
    mock_app = MagicMock()
    mock_win = MagicMock()
    mock_win.descendants.return_value = [mock_ctrl]
    mock_app.window.return_value = mock_win

    with patch("agent.tools.ui_tree.ctypes") as mock_ctypes:
        mock_ctypes.windll.user32.GetForegroundWindow.return_value = 12345
        with patch("agent.tools.ui_tree.Application", return_value=mock_app):
            tool = make_get_ui_tree("claude-sonnet-4-6")
            result = tool.invoke({})

    controls = json.loads(result)
    assert len(controls) == 1
    assert controls[0]["label"] == "Next"
    assert controls[0]["type"] == "Button"
    assert controls[0]["x"] == 150  # (100+200)//2
    assert controls[0]["y"] == 65   # (50+80)//2


def test_filters_out_non_interactive_controls():
    interactive = _make_mock_control("Button", "OK")
    non_interactive = _make_mock_control("Text", "Please read the license")
    mock_app = MagicMock()
    mock_win = MagicMock()
    mock_win.descendants.return_value = [interactive, non_interactive]
    mock_app.window.return_value = mock_win

    with patch("agent.tools.ui_tree.ctypes") as mock_ctypes:
        mock_ctypes.windll.user32.GetForegroundWindow.return_value = 12345
        with patch("agent.tools.ui_tree.Application", return_value=mock_app):
            tool = make_get_ui_tree("claude-sonnet-4-6")
            result = tool.invoke({})

    controls = json.loads(result)
    assert len(controls) == 1
    assert controls[0]["label"] == "OK"


def test_falls_back_to_vision_when_ui_automation_raises():
    vision_controls = [{"type": "Button", "label": "Install", "x": 400, "y": 300}]

    with patch("agent.tools.ui_tree.ctypes") as mock_ctypes:
        mock_ctypes.windll.user32.GetForegroundWindow.side_effect = Exception("no window")
        with patch("agent.tools.ui_tree._vision_fallback", return_value=vision_controls) as mock_vision:
            tool = make_get_ui_tree("claude-sonnet-4-6")
            result = tool.invoke({})
            mock_vision.assert_called_once_with("claude-sonnet-4-6")

    controls = json.loads(result)
    assert controls[0]["label"] == "Install"


def test_falls_back_to_vision_when_descendants_empty():
    mock_app = MagicMock()
    mock_win = MagicMock()
    mock_win.descendants.return_value = []
    mock_app.window.return_value = mock_win
    vision_controls = [{"type": "Button", "label": "Next", "x": 300, "y": 400}]

    with patch("agent.tools.ui_tree.ctypes") as mock_ctypes:
        mock_ctypes.windll.user32.GetForegroundWindow.return_value = 12345
        with patch("agent.tools.ui_tree.Application", return_value=mock_app):
            with patch("agent.tools.ui_tree._vision_fallback", return_value=vision_controls):
                tool = make_get_ui_tree("claude-sonnet-4-6")
                result = tool.invoke({})

    controls = json.loads(result)
    assert controls[0]["label"] == "Next"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/tools/test_ui_tree.py -v
```

Expected: `ModuleNotFoundError: No module named 'agent.tools.ui_tree'`

- [ ] **Step 3: Implement `agent/tools/ui_tree.py`**

```python
import ctypes
import io
import json
import base64
import re
from typing import Optional
from langchain_core.tools import tool
from pywinauto.application import Application

_INTERACTIVE_TYPES = {"Button", "CheckBox", "RadioButton", "Edit", "ComboBox"}


def _try_ui_automation() -> list:
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    app = Application(backend="uia").connect(handle=hwnd)
    win = app.window(handle=hwnd)
    controls = []
    for ctrl in win.descendants():
        try:
            ctrl_type = ctrl.element_info.control_type
            if ctrl_type not in _INTERACTIVE_TYPES:
                continue
            label = ctrl.window_text()
            rect = ctrl.rectangle()
            controls.append({
                "type": ctrl_type,
                "label": label,
                "x": (rect.left + rect.right) // 2,
                "y": (rect.top + rect.bottom) // 2,
            })
        except Exception:
            continue
    return controls


def _vision_fallback(model: str) -> list:
    import mss
    import litellm
    from PIL import Image

    with mss.mss() as sct:
        raw = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode()

    response = litellm.completion(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "This is a screenshot of a Windows installer. "
                        "List all interactive elements (buttons, checkboxes, text fields). "
                        "Return ONLY a JSON array. Each object must have: "
                        "\"type\" (Button/CheckBox/Edit/RadioButton), "
                        "\"label\" (the visible text on the element), "
                        "\"x\" (center x pixel coordinate), "
                        "\"y\" (center y pixel coordinate). "
                        "Example: [{\"type\": \"Button\", \"label\": \"Next\", \"x\": 450, \"y\": 380}]"
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{encoded}"},
                },
            ],
        }],
    )

    content = response.choices[0].message.content
    match = re.search(r"\[.*\]", content, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return []


def make_get_ui_tree(model: str):
    @tool("get_ui_tree")
    def get_ui_tree() -> str:
        """Get interactive UI elements from the foreground installer window. Tries Windows accessibility tree first, falls back to LLM vision if unavailable. Returns a JSON array of controls with type, label, x, y fields."""
        try:
            controls = _try_ui_automation()
        except Exception:
            controls = []

        if not controls:
            controls = _vision_fallback(model)

        return json.dumps(controls)

    return get_ui_tree
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/tools/test_ui_tree.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/tools/ui_tree.py tests/tools/test_ui_tree.py
git commit -m "feat: add get_ui_tree tool with vision fallback"
```

---

## Task 4: `click_element` Tool

**Files:**
- Create: `agent/tools/click.py`
- Create: `tests/tools/test_click.py`

- [ ] **Step 1: Write failing tests**

`tests/tools/test_click.py`:
```python
from unittest.mock import patch, MagicMock
from agent.tools.click import click_element


def test_click_by_label_uses_pywinauto():
    mock_app = MagicMock()
    mock_win = MagicMock()
    mock_ctrl = MagicMock()
    mock_app.window.return_value = mock_win
    mock_win.child_window.return_value = mock_ctrl

    with patch("agent.tools.click.ctypes") as mock_ctypes:
        mock_ctypes.windll.user32.GetForegroundWindow.return_value = 12345
        with patch("agent.tools.click.Application", return_value=mock_app):
            result = click_element.invoke({"label": "Next"})

    mock_ctrl.click_input.assert_called_once()
    assert "Next" in result


def test_click_by_coordinates_uses_pyautogui():
    with patch("agent.tools.click.pyautogui.click") as mock_click:
        result = click_element.invoke({"x": 400, "y": 300})

    mock_click.assert_called_once_with(400, 300)
    assert "400" in result
    assert "300" in result


def test_click_by_label_falls_back_to_coordinates_on_failure():
    mock_app = MagicMock()
    mock_win = MagicMock()
    mock_win.child_window.side_effect = Exception("control not found")
    mock_app.window.return_value = mock_win

    with patch("agent.tools.click.ctypes") as mock_ctypes:
        mock_ctypes.windll.user32.GetForegroundWindow.return_value = 12345
        with patch("agent.tools.click.Application", return_value=mock_app):
            with patch("agent.tools.click.pyautogui.click") as mock_pyautogui:
                result = click_element.invoke({"label": "Next", "x": 400, "y": 300})

    mock_pyautogui.assert_called_once_with(400, 300)
    assert "400" in result


def test_click_returns_error_when_no_label_or_coords():
    result = click_element.invoke({})
    assert "error" in result.lower()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/tools/test_click.py -v
```

Expected: `ModuleNotFoundError: No module named 'agent.tools.click'`

- [ ] **Step 3: Implement `agent/tools/click.py`**

```python
import ctypes
from typing import Optional
import pyautogui
from langchain_core.tools import tool
from pywinauto.application import Application


@tool
def click_element(label: Optional[str] = None, x: Optional[int] = None, y: Optional[int] = None) -> str:
    """Click a UI element in the installer. Provide 'label' to click by button text using accessibility, or 'x' and 'y' for pixel coordinates. If label is given but not found, falls back to coordinates."""
    if label is None and (x is None or y is None):
        return "error: provide either label or both x and y coordinates"

    if label is not None:
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            app = Application(backend="uia").connect(handle=hwnd)
            win = app.window(handle=hwnd)
            ctrl = win.child_window(title=label, control_type="Button")
            ctrl.click_input()
            return f"Clicked button '{label}' via accessibility."
        except Exception:
            if x is not None and y is not None:
                pyautogui.click(x, y)
                return f"Clicked '{label}' via coordinates ({x}, {y}) after accessibility lookup failed."
            return f"error: could not find button '{label}' and no coordinates provided"

    pyautogui.click(x, y)
    return f"Clicked coordinates ({x}, {y})."
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/tools/test_click.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/tools/click.py tests/tools/test_click.py
git commit -m "feat: add click_element tool"
```

---

## Task 5: `type_text` Tool

**Files:**
- Create: `agent/tools/type_text.py`
- Create: `tests/tools/test_type_text.py`

- [ ] **Step 1: Write failing tests**

`tests/tools/test_type_text.py`:
```python
from unittest.mock import patch
from agent.tools.type_text import type_text


def test_types_text_using_pyautogui():
    with patch("agent.tools.type_text.pyautogui.typewrite") as mock_typewrite:
        result = type_text.invoke({"text": "C:\\MyApp"})

    mock_typewrite.assert_called_once_with("C:\\MyApp", interval=0.05)
    assert "C:\\MyApp" in result


def test_types_empty_string():
    with patch("agent.tools.type_text.pyautogui.typewrite") as mock_typewrite:
        result = type_text.invoke({"text": ""})

    mock_typewrite.assert_called_once_with("", interval=0.05)
    assert "Typed" in result
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/tools/test_type_text.py -v
```

Expected: `ModuleNotFoundError: No module named 'agent.tools.type_text'`

- [ ] **Step 3: Implement `agent/tools/type_text.py`**

```python
import pyautogui
from langchain_core.tools import tool


@tool
def type_text(text: str) -> str:
    """Type text into the currently focused input field. Use for install path prompts, license keys, or any text field in the installer."""
    pyautogui.typewrite(text, interval=0.05)
    return f"Typed: {text}"
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/tools/test_type_text.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/tools/type_text.py tests/tools/test_type_text.py
git commit -m "feat: add type_text tool"
```

---

## Task 6: Tools Factory + `prompts.py`

**Files:**
- Modify: `agent/tools/__init__.py`
- Create: `agent/prompts.py`

- [ ] **Step 1: Implement `agent/tools/__init__.py`**

```python
from langchain_core.tools import BaseTool
from agent.tools.ui_tree import make_get_ui_tree
from agent.tools.click import click_element
from agent.tools.type_text import type_text
from agent.tools.wait import wait


def build_tools(model: str) -> list[BaseTool]:
    return [make_get_ui_tree(model), click_element, type_text, wait]
```

- [ ] **Step 2: Implement `agent/prompts.py`**

```python
SYSTEM_PROMPT = """You are a Windows installer automation agent. Your job is to click through a Windows installer GUI until the installation is complete.

## Tools
- `get_ui_tree`: Get interactive elements from the installer window. Call this at the start of every step.
- `click_element`: Click a button by label or pixel coordinates.
- `type_text`: Type text into a focused input field.
- `wait`: Wait N seconds for loading screens or progress bars.

## Rules
1. Always call `get_ui_tree` first to see what's on screen.
2. Click buttons in this priority order: Finish > Next > Accept > Agree > Install > Yes > OK > Continue
3. Never click: Cancel, Decline, No, Quit, Exit, Uninstall.
4. If a license agreement checkbox appears, check it before clicking Accept/Next.
5. After clicking "Install", call `wait` with 10 seconds before checking again.
6. If `get_ui_tree` returns an empty list, call `wait` with 2 seconds then try again once.
7. After clicking "Finish" and `get_ui_tree` returns empty, the installation is complete.

## Completion
When installation is complete, respond: "Installation complete."
"""
```

- [ ] **Step 3: Verify import works**

```bash
uv run python -c "from agent.tools import build_tools; from agent.prompts import SYSTEM_PROMPT; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add agent/tools/__init__.py agent/prompts.py
git commit -m "feat: add tools factory and system prompt"
```

---

## Task 7: `agent.py`

**Files:**
- Create: `agent/agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: Write failing tests**

`tests/test_agent.py`:
```python
import os
from unittest.mock import patch, MagicMock
from langchain.agents import AgentExecutor
from agent.agent import build_agent


def test_build_agent_returns_agent_executor():
    with patch.dict(os.environ, {"MODEL": "claude-sonnet-4-6", "ANTHROPIC_API_KEY": "test-key"}):
        with patch("agent.agent.ChatLiteLLM") as mock_llm_cls:
            mock_llm_cls.return_value = MagicMock()
            executor = build_agent()
    assert isinstance(executor, AgentExecutor)


def test_build_agent_uses_model_env_var():
    with patch.dict(os.environ, {"MODEL": "gpt-4o", "OPENAI_API_KEY": "test-key"}):
        with patch("agent.agent.ChatLiteLLM") as mock_llm_cls:
            mock_llm_cls.return_value = MagicMock()
            build_agent()
    mock_llm_cls.assert_called_once_with(model="gpt-4o")


def test_build_agent_respects_max_steps_env_var():
    with patch.dict(os.environ, {"MODEL": "claude-sonnet-4-6", "ANTHROPIC_API_KEY": "test", "MAX_STEPS": "15"}):
        with patch("agent.agent.ChatLiteLLM") as mock_llm_cls:
            mock_llm_cls.return_value = MagicMock()
            executor = build_agent()
    assert executor.max_iterations == 15
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_agent.py -v
```

Expected: `ModuleNotFoundError: No module named 'agent.agent'`

- [ ] **Step 3: Implement `agent/agent.py`**

```python
import os
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.prompts import ChatPromptTemplate
from agent.prompts import SYSTEM_PROMPT
from agent.tools import build_tools


def build_agent() -> AgentExecutor:
    model = os.getenv("MODEL", "claude-sonnet-4-6")
    max_steps = int(os.getenv("MAX_STEPS", "30"))

    llm = ChatLiteLLM(model=model)
    tools = build_tools(model)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
    return AgentExecutor(agent=agent, tools=tools, max_iterations=max_steps, verbose=True)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_agent.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/agent.py tests/test_agent.py
git commit -m "feat: add build_agent with LangChain AgentExecutor"
```

---

## Task 8: `main.py` CLI Entry Point

**Files:**
- Create: `main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write failing tests**

`tests/test_main.py`:
```python
import subprocess
from unittest.mock import patch, MagicMock
from main import run


def test_run_launches_installer_subprocess():
    mock_executor = MagicMock()
    mock_executor.invoke.return_value = {"output": "Installation complete."}

    with patch("main.subprocess.Popen") as mock_popen:
        with patch("main.build_agent", return_value=mock_executor):
            run("C:\\fake\\installer.exe")

    mock_popen.assert_called_once_with(["C:\\fake\\installer.exe"])


def test_run_invokes_agent_with_task():
    mock_executor = MagicMock()
    mock_executor.invoke.return_value = {"output": "Installation complete."}

    with patch("main.subprocess.Popen"):
        with patch("main.build_agent", return_value=mock_executor):
            run("C:\\fake\\installer.exe")

    call_input = mock_executor.invoke.call_args[0][0]["input"]
    assert "installer.exe" in call_input or "install" in call_input.lower()


def test_run_prints_result(capsys):
    mock_executor = MagicMock()
    mock_executor.invoke.return_value = {"output": "Installation complete."}

    with patch("main.subprocess.Popen"):
        with patch("main.build_agent", return_value=mock_executor):
            run("C:\\fake\\installer.exe")

    captured = capsys.readouterr()
    assert "Installation complete." in captured.out
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_main.py -v
```

Expected: `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Implement `main.py`**

```python
import argparse
import subprocess
from dotenv import load_dotenv
from agent.agent import build_agent


def run(installer_path: str) -> None:
    load_dotenv()
    subprocess.Popen([installer_path])
    executor = build_agent()
    result = executor.invoke({
        "input": f"Click through the installer that just opened ({installer_path}) until installation is complete."
    })
    print(result["output"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Automatically click through a Windows installer.")
    parser.add_argument("--installer", required=True, help="Path to the .exe installer file")
    args = parser.parse_args()
    run(args.installer)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_main.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Run the full test suite**

```bash
uv run pytest -v
```

Expected: all tests pass (no failures).

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: add CLI entry point"
```

---

## Task 9: Smoke Test Against a Real Installer

> Run this manually on the Windows VM. No automated test — this validates the full end-to-end flow.

- [ ] **Step 1: Copy a test installer to the VM**

Use a known-safe installer such as Zoom: `C:\Users\wangz\Downloads\ZoomInstallerFull.exe`

- [ ] **Step 2: Create a `.env` file from the example**

```bash
cp .env.example .env
# edit .env and fill in MODEL and the appropriate API key
```

- [ ] **Step 3: Run the agent**

```bash
uv run python main.py --installer "C:\Users\wangz\Downloads\ZoomInstallerFull.exe"
```

Expected: installer window appears, agent prints tool calls in verbose output, buttons are clicked one by one, agent prints "Installation complete." when done.

- [ ] **Step 4: Verify via VM snapshot**

Revert the VM snapshot to confirm the base image is clean, then re-run to confirm reproducibility.
