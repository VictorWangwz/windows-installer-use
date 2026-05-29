from unittest.mock import patch, MagicMock
from main import run


def test_run_launches_installer_subprocess():
    mock_executor = MagicMock()
    mock_executor.invoke.return_value = {"messages": [MagicMock(content="Installation complete.")]}

    with patch("main.load_dotenv"):
        with patch("main.subprocess.Popen") as mock_popen:
            with patch("main.build_agent", return_value=mock_executor):
                with patch("main.os.path.isfile", return_value=True):
                    run("C:\\fake\\installer.exe")

    mock_popen.assert_called_once_with(["C:\\fake\\installer.exe"])


def test_run_invokes_agent_with_task():
    mock_executor = MagicMock()
    mock_executor.invoke.return_value = {"messages": [MagicMock(content="Installation complete.")]}

    with patch("main.load_dotenv"):
        with patch("main.subprocess.Popen"):
            with patch("main.build_agent", return_value=mock_executor):
                with patch("main.os.path.isfile", return_value=True):
                    run("C:\\fake\\installer.exe")

    call_messages = mock_executor.invoke.call_args[0][0]["messages"]
    assert len(call_messages) == 1
    assert "C:\\fake\\installer.exe" in call_messages[0].content


def test_run_prints_result(capsys):
    mock_executor = MagicMock()
    mock_executor.invoke.return_value = {"messages": [MagicMock(content="Installation complete.")]}

    with patch("main.load_dotenv"):
        with patch("main.subprocess.Popen"):
            with patch("main.build_agent", return_value=mock_executor):
                with patch("main.os.path.isfile", return_value=True):
                    run("C:\\fake\\installer.exe")

    captured = capsys.readouterr()
    assert "Installation complete." in captured.out
