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
