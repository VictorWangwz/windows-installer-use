import ctypes
import io
import json
import base64
from langchain_core.tools import tool
from pywinauto.application import Application

_INTERACTIVE_TYPES = {"Button", "CheckBox", "RadioButton", "Edit", "ComboBox"}


def _try_ui_automation() -> list:
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    app = Application(backend="uia")
    app.connect(handle=hwnd)
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


def _extract_json_array(content: str) -> list:
    start = content.find("[")
    if start == -1:
        return []
    depth = 0
    for i, ch in enumerate(content[start:], start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(content[start:i + 1])
                except json.JSONDecodeError:
                    return []
    return []


def _vision_fallback(model: str) -> list:
    import mss
    import litellm
    from PIL import Image

    with mss.mss() as sct:
        monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        raw = sct.grab(monitor)
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
                        "\"type\" (Button/CheckBox/Edit/RadioButton/ComboBox), "
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
    return _extract_json_array(content)


def make_get_ui_tree(model: str):
    @tool("get_ui_tree")
    def get_ui_tree() -> str:
        """Get interactive UI elements from the foreground installer window. Tries Windows accessibility tree first, falls back to LLM vision if unavailable. Returns a JSON array of controls with type, label, x, y fields."""
        try:
            controls = _try_ui_automation()
        except Exception:
            controls = []

        if not controls:
            try:
                controls = _vision_fallback(model)
            except Exception:
                controls = []

        return json.dumps(controls)

    return get_ui_tree
