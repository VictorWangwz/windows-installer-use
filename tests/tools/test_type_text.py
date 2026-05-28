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
