import os
from unittest.mock import patch, MagicMock
from agent.agent import build_agent, AgentExecutor
from agent.prompts import SYSTEM_PROMPT


def test_build_agent_returns_agent_executor():
    mock_graph = MagicMock()
    mock_llm = MagicMock()
    with patch.dict(os.environ, {"MODEL": "glm-5.1", "OPENAI_API_KEY": "test-key", "OPENAI_API_BASE": "https://example.com"}):
        with patch("agent.agent._build_llm", return_value=mock_llm):
            with patch("agent.agent.create_agent", return_value=mock_graph):
                executor = build_agent()
    assert isinstance(executor, AgentExecutor)


def test_build_agent_uses_model_env_var():
    mock_graph = MagicMock()
    mock_llm = MagicMock()
    with patch.dict(os.environ, {"MODEL": "glm-5.1", "OPENAI_API_KEY": "test-key", "OPENAI_API_BASE": "https://example.com"}):
        with patch("agent.agent._build_llm", return_value=mock_llm) as mock_build_llm:
            with patch("agent.agent.create_agent", return_value=mock_graph) as mock_create:
                build_agent()
    mock_build_llm.assert_called_once_with("glm-5.1")
    assert mock_create.call_args[1]["system_prompt"] == SYSTEM_PROMPT


def test_build_agent_respects_max_steps_env_var():
    mock_graph = MagicMock()
    mock_llm = MagicMock()
    with patch.dict(os.environ, {"MODEL": "glm-5.1", "OPENAI_API_KEY": "test-key", "OPENAI_API_BASE": "https://example.com", "MAX_STEPS": "15"}):
        with patch("agent.agent._build_llm", return_value=mock_llm):
            with patch("agent.agent.create_agent", return_value=mock_graph):
                executor = build_agent()
    assert executor.max_iterations == 15
