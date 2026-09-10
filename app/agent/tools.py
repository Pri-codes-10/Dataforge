import asyncio
import logging
import re
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings
from app.agent.state import conversation_state

logger = logging.getLogger("sutra.tools")

CITY_TO_IATA = {
    "kolkata": "CCU",
    "calcutta": "CCU",
    "delhi": "DEL",
    "new delhi": "DEL",
    "mumbai": "BOM",
    "bombay": "BOM",
    "bangalore": "BLR",
    "bengaluru": "BLR",
    "chennai": "MAA",
    "madras": "MAA",
    "hyderabad": "HYD",
    "pune": "PNQ",
    "goa": "GOI",
    "jaipur": "JAI",
    "ahmedabad": "AMD",
    "lucknow": "LKO",
    "patna": "PAT",
    "guwahati": "GAU",
    "kochi": "COK",
}


def resolve_iata(city_name: str, default: str = "CCU") -> str:
    """Resolve a city or airport name to an IATA 3-letter code."""
    if not city_name:
        return default
    c = city_name.strip().lower()
    if len(c) == 3 and c.isalpha():
        return c.upper()
    for name, code in CITY_TO_IATA.items():
        if name in c or c in name:
            return code
    return default


async def search_flights(
    origin: str = "",
    destination: str = "",
    date: str = "",
    max_price: str = "",
    **kwargs,
) -> Dict[str, Any]:
    """
    Search real flights using Aviationstack API.
    Does NOT return synthetic or fake flight data.
    """
    api_key = settings.FLIGHT_API_KEY
    if not api_key:
        logger.info("[Flight API] FLIGHT_API_KEY not configured in .env. Reporting service unavailable.")
        return {
            "success": False,
            "tool": "search_flights",
            "error": "FLIGHT_API_KEY_NOT_CONFIGURED",
            "message": "Flight search API key is not configured. Please add FLIGHT_API_KEY to your environment.",
            "result": "Sorry, flight search is unavailable right now because the flight API key is not configured.",
        }

    dep_iata = resolve_iata(origin, "CCU")
    arr_iata = resolve_iata(destination, "DEL")

    url = "http://api.aviationstack.com/v1/flights"
    params = {
        "access_key": api_key,
        "dep_iata": dep_iata,
        "arr_iata": arr_iata,
        "limit": 5,
    }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                err_info = data["error"].get("message") or str(data["error"])
                logger.error(f"[Flight API] Provider error: {err_info}")
                return {
                    "success": False,
                    "tool": "search_flights",
                    "error": err_info,
                    "message": "Flight service returned an error.",
                    "result": "Sorry, the flight service returned an error. Please try again later.",
                }

            flights = data.get("data", [])
            if not flights:
                return {
                    "success": True,
                    "tool": "search_flights",
                    "origin": origin or dep_iata,
                    "destination": destination or arr_iata,
                    "date": date or "today",
                    "result": f"No active flights found between {dep_iata} and {arr_iata} for {date or 'the requested date'}.",
                }

            summaries = []
            for f in flights[:3]:
                airline = f.get("airline", {}).get("name", "Airline")
                flight_num = f.get("flight", {}).get("iata", "Flight")
                dep_time = (f.get("departure", {}).get("scheduled") or "")[11:16] or "scheduled"
                status = f.get("flight_status", "scheduled")
                summaries.append(f"{airline} {flight_num} departing at {dep_time} ({status})")

            flight_text = "; ".join(summaries)
            return {
                "success": True,
                "tool": "search_flights",
                "origin": origin or dep_iata,
                "destination": destination or arr_iata,
                "date": date,
                "flights_count": len(flights),
                "result": f"Found flights from {dep_iata} to {arr_iata}: {flight_text}.",
            }
    except Exception as exc:
        logger.error(f"[Flight API] Failed to query flights: {exc}")
        return {
            "success": False,
            "tool": "search_flights",
            "error": str(exc),
            "result": "Sorry, flight search is currently unavailable.",
        }


async def search_hotels(
    city: str = "",
    date: str = "",
    max_price: str = "",
    **kwargs,
) -> Dict[str, Any]:
    """
    Search hotels tool.
    Honestly indicates that hotel search is not currently integrated, avoiding fake results.
    """
    return {
        "success": False,
        "tool": "search_hotels",
        "city": city,
        "available": False,
        "message": "Hotel search is not currently integrated.",
        "result": "Sorry, hotel search isn't available right now. But I can help you with flights or general information.",
    }


async def search_information(query: str = "", **kwargs) -> Dict[str, Any]:
    """
    Real live web information retrieval tool.
    Fetches real-time information for weather, news, sports, current events, and general queries.
    Uses Tavily if WEB_SEARCH_API_KEY is configured, or live HTTP web retrieval.
    """
    clean_query = query.strip()
    if not clean_query:
        return {
            "success": False,
            "tool": "search_information",
            "result": "No query provided.",
        }

    # 1. Check for Tavily search API key
    web_api_key = settings.WEB_SEARCH_API_KEY
    if web_api_key:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    "https://api.tavily.com/search",
                    json={"api_key": web_api_key, "query": clean_query, "max_results": 3},
                )
                if r.status_code == 200:
                    tavily_data = r.json()
                    results = tavily_data.get("results", [])
                    if results:
                        snippets = [res.get("content", "") for res in results[:2] if res.get("content")]
                        combined = " ".join(snippets)[:300]
                        return {
                            "success": True,
                            "tool": "search_information",
                            "query": clean_query,
                            "source": "tavily",
                            "result": combined or f"Information found for {clean_query}",
                        }
        except Exception as e:
            logger.warning(f"[WebSearch] Tavily query failed, falling back to live web: {e}")

    # 2. Live HTTP Web Search (DuckDuckGo HTML retrieval)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": clean_query},
                headers=headers,
            )
            if resp.status_code == 200:
                raw_snippets = re.findall(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
                clean_snippets = [
                    re.sub(r"&[a-zA-Z0-9#]+;", " ", re.sub(r"<[^>]+>", "", s)).strip()
                    for s in raw_snippets[:2]
                    if s.strip()
                ]
                if clean_snippets:
                    combined = " ".join(clean_snippets)[:300]
                    return {
                        "success": True,
                        "tool": "search_information",
                        "query": clean_query,
                        "source": "live_web",
                        "result": combined,
                    }
    except Exception as exc:
        logger.error(f"[WebSearch] Live web search failed: {exc}")

    return {
        "success": False,
        "tool": "search_information",
        "query": clean_query,
        "result": f"I couldn't retrieve live search results for {clean_query} right now.",
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
    Execute a tool while protecting conversation state from stale results.
    """
    tool = TOOLS.get(tool_name, search_information)

    current_id = task_id or conversation_state.active_task_id or conversation_state.start_task()
    current_ver = task_version if task_version is not None else conversation_state.task_version

    try:
        result = await tool(**arguments)

        # Check whether the user changed the task while this tool was running
        if not conversation_state.is_task_current(current_id, current_ver):
            return {
                "success": False,
                "stale": True,
                "requestId": current_id,
                "task_version": current_ver,
                "message": f"Tool result for {current_id} (v{current_ver}) is outdated.",
            }

        result["requestId"] = current_id
        result["task_version"] = current_ver

        # Record tool result in conversation state
        if result.get("result"):
            conversation_state.add_tool_result(tool_name, result["result"])

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