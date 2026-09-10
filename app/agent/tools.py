import asyncio
from typing import Any, Dict, Optional

from app.agent.state import conversation_state


async def search_flights(origin: str = "", destination: str = "", date: str = "", max_price: str = "", **kwargs) -> Dict[str, Any]:
    """
    Search flights tool representing external airline booking API.
    Simulates a 4-second delay for realistic async execution and testing stale cancellation.
    """
    await asyncio.sleep(4)
    price_info = f" under {max_price}" if max_price else ""
    return {
        "success": True,
        "tool": "search_flights",
        "origin": origin,
        "destination": destination,
        "date": date,
        "result": f"Found flights from {origin or 'Kolkata'} to {destination or 'Delhi'} for {date or 'tomorrow'}{price_info}. Lowest fare: ₹4,850.",
    }


async def search_hotels(city: str = "", date: str = "", max_price: str = "", **kwargs) -> Dict[str, Any]:
    """
    Search hotels tool.
    """
    await asyncio.sleep(4)
    return {
        "success": True,
        "tool": "search_hotels",
        "city": city,
        "date": date,
        "result": f"Found 8 top-rated hotels in {city or 'Kolkata'} for {date or 'this weekend'}.",
    }


async def search_information(query: str = "", **kwargs) -> Dict[str, Any]:
    """
    General search tool.
    """
    await asyncio.sleep(3)
    return {
        "success": True,
        "tool": "search_information",
        "query": query,
        "result": f"Information retrieved for: {query}",
    }


TOOLS = {
    "search_flights": search_flights,
    "search_hotels": search_hotels,
    "search_information": search_information,
}


async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    task_id: Optional[str] = None,
    task_version: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Execute a tool while protecting the conversation state
    from stale results.
    """
    tool = TOOLS.get(tool_name, search_information)

    current_id = task_id or conversation_state.active_task_id or conversation_state.start_task()
    current_ver = task_version if task_version is not None else conversation_state.task_version

    try:
        result = await tool(**arguments)

        # Check whether the user changed the task while
        # this tool was running.
        if not conversation_state.is_task_current(
            current_id,
            current_ver,
        ):
            return {
                "success": False,
                "stale": True,
                "requestId": current_id,
                "task_version": current_ver,
                "message": f"Tool result for {current_id} (v{current_ver}) is outdated.",
            }

        result["requestId"] = current_id
        result["task_version"] = current_ver
        return result

    except asyncio.CancelledError:
        return {
            "success": False,
            "cancelled": True,
            "requestId": current_id,
            "task_version": current_ver,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "requestId": current_id,
            "task_version": current_ver,
        }