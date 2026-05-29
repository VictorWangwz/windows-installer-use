import os
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool

from agent.prompts import SYSTEM_PROMPT
from agent.tools import build_tools


class ChatLiteLLM(BaseChatModel):
    """LiteLLM-backed chat model using langchain's init_chat_model."""

    model: str = "claude-sonnet-4-6"

    @property
    def _llm_type(self) -> str:
        return "litellm"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        from langchain.chat_models import init_chat_model

        llm = init_chat_model(self.model)
        return llm._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


class AgentExecutor:
    """Thin wrapper around a LangGraph CompiledStateGraph that exposes the
    ``max_iterations`` attribute expected by callers."""

    def __init__(
        self,
        graph: Any,
        tools: list[BaseTool],
        max_iterations: int = 30,
        verbose: bool = False,
    ) -> None:
        self._graph = graph
        self.tools = tools
        self.max_iterations = max_iterations
        self.verbose = verbose

    def invoke(self, input: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        config = RunnableConfig(recursion_limit=self.max_iterations)
        return self._graph.invoke(input, config=config, **kwargs)

    def stream(self, input: dict[str, Any], **kwargs: Any):
        config = RunnableConfig(recursion_limit=self.max_iterations)
        yield from self._graph.stream(input, config=config, **kwargs)


def build_agent() -> AgentExecutor:
    model = os.getenv("MODEL", "claude-sonnet-4-6")
    max_steps = int(os.getenv("MAX_STEPS", "30"))

    llm = ChatLiteLLM(model=model)
    tools = build_tools(model)

    graph = create_agent(llm, tools=tools, system_prompt=SYSTEM_PROMPT)
    return AgentExecutor(graph=graph, tools=tools, max_iterations=max_steps, verbose=True)
