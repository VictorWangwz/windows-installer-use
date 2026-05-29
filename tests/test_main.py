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
    assert "C:\\fake\\installer.exe" in call_input


def test_run_prints_result(capsys):
    mock_executor = MagicMock()
    mock_executor.invoke.return_value = {"output": "Installation complete."}

    with patch("main.subprocess.Popen"):
        with patch("main.build_agent", return_value=mock_executor):
            run("C:\\fake\\installer.exe")

    captured = capsys.readouterr()
    assert "Installation complete." in captured.out
