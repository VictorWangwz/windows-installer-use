import os
from typing import Any

from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool

from agent.prompts import SYSTEM_PROMPT
from agent.tools import build_tools


class AgentExecutor:
    """Wraps a LangGraph CompiledStateGraph to expose max_iterations and invoke."""

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
    model = os.getenv("MODEL", "anthropic:claude-sonnet-4-6")
    max_steps = int(os.getenv("MAX_STEPS", "30"))

    tools = build_tools(model)
    graph = create_agent(model, tools=tools, system_prompt=SYSTEM_PROMPT)
    return AgentExecutor(graph=graph, tools=tools, max_iterations=max_steps, verbose=True)
