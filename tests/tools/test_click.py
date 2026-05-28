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
        with patch("agent.tools.click.Application", return_value=mock_app) as mock_app_class:
            result = click_element.invoke({"label": "Next"})

    mock_app_class.assert_called_once_with(backend="uia")
    mock_app.connect.assert_called_once_with(handle=12345)
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
