from langchain_core.tools import BaseTool
from agent.tools.ui_tree import make_get_ui_tree
from agent.tools.click import click_element
from agent.tools.type_text import type_text
from agent.tools.wait import wait


def build_tools(model: str) -> list[BaseTool]:
    return [make_get_ui_tree(model), click_element, type_text, wait]
