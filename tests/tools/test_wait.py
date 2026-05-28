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
