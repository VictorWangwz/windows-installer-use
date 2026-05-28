import time
from langchain_core.tools import tool


@tool
def wait(seconds: int = 2) -> str:
    """Wait for the specified number of seconds. Use after clicking Install or any action that triggers a loading screen or progress bar."""
    time.sleep(seconds)
    return f"Waited {seconds} seconds."
