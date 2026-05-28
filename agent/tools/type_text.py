import pyautogui
from langchain_core.tools import tool


@tool
def type_text(text: str) -> str:
    """Type text into the currently focused input field. Use for install path prompts, license keys, or any text field in the installer."""
    pyautogui.typewrite(text, interval=0.05)
    return f"Typed: {text}"
