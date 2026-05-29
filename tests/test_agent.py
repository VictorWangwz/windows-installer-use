import os
from unittest.mock import patch, MagicMock
from agent.agent import build_agent, AgentExecutor
from agent.prompts import SYSTEM_PROMPT


def test_build_agent_returns_agent_executor():
    mock_graph = MagicMock()
    with patch.dict(os.environ, {"MODEL": "anthropic:claude-sonnet-4-6", "ANTHROPIC_API_KEY": "test-key"}):
        with patch("agent.agent.create_agent", return_value=mock_graph):
            executor = build_agent()
    assert isinstance(executor, AgentExecutor)


def test_build_agent_uses_model_env_var():
    mock_graph = MagicMock()
    with patch.dict(os.environ, {"MODEL": "openai:gpt-4o", "OPENAI_API_KEY": "test-key"}):
        with patch("agent.agent.create_agent", return_value=mock_graph) as mock_create:
            build_agent()
    call_args = mock_create.call_args
    assert call_args[0][0] == "openai:gpt-4o"
    assert call_args[1]["system_prompt"] == SYSTEM_PROMPT


def test_build_agent_respects_max_steps_env_var():
    mock_graph = MagicMock()
    with patch.dict(os.environ, {"MODEL": "anthropic:claude-sonnet-4-6", "ANTHROPIC_API_KEY": "test", "MAX_STEPS": "15"}):
        with patch("agent.agent.create_agent", return_value=mock_graph):
            executor = build_agent()
    assert executor.max_iterations == 15
