import os
from unittest.mock import patch, MagicMock
from agent.agent import build_agent, AgentExecutor


def test_build_agent_returns_agent_executor():
    with patch.dict(os.environ, {"MODEL": "claude-sonnet-4-6", "ANTHROPIC_API_KEY": "test-key"}):
        with patch("agent.agent.ChatLiteLLM") as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_llm_cls.return_value = mock_llm
            executor = build_agent()
    assert isinstance(executor, AgentExecutor)


def test_build_agent_uses_model_env_var():
    with patch.dict(os.environ, {"MODEL": "gpt-4o", "OPENAI_API_KEY": "test-key"}):
        with patch("agent.agent.ChatLiteLLM") as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_llm_cls.return_value = mock_llm
            build_agent()
    mock_llm_cls.assert_called_once_with(model="gpt-4o")


def test_build_agent_respects_max_steps_env_var():
    with patch.dict(os.environ, {"MODEL": "claude-sonnet-4-6", "ANTHROPIC_API_KEY": "test", "MAX_STEPS": "15"}):
        with patch("agent.agent.ChatLiteLLM") as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_llm_cls.return_value = mock_llm
            executor = build_agent()
    assert executor.max_iterations == 15
