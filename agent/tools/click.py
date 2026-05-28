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
            app = Application(backend="uia")
            app.connect(handle=hwnd)
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
