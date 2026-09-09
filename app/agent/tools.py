import asyncio
from typing import Any, Dict

from app.agent.state import conversation_state


async def search_information(query: str) -> Dict[str, Any]:
    """
    Demo tool representing an external/long-running operation.

    The delay is intentionally kept for the demo so we can test
    interruption and stale-result handling.
    """

    await asyncio.sleep(5)

    return {
        "success": True,
        "query": query,
        "result": f"Information found for: {query}",
    }


TOOLS = {
    "search_information": search_information,
}


async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a tool while protecting the conversation state
    from stale results.
    """

    tool = TOOLS.get(tool_name)

    if tool is None:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}",
        }

    task_id = conversation_state.start_task()
    task_version = conversation_state.task_version

    try:
        result = await tool(**arguments)

        # Check whether the user changed the task while
        # this tool was running.
        if not conversation_state.is_task_current(
            task_id,
            task_version,
        ):
            return {
                "success": False,
                "stale": True,
                "message": "Tool result is outdated.",
            }

        return result

    except asyncio.CancelledError:
        conversation_state.cancel_task()
        raise

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }