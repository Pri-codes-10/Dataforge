"""Deterministic replay: python -m app.demo. Does not use live providers."""
import asyncio
import json
from pathlib import Path
from .orchestrator import Action, Orchestrator
from .playback import MemoryPlayback


async def main():
    fixtures = json.loads((Path(__file__).parents[1] / "fixtures/turns.json").read_text(encoding="utf-8"))
    async def planner(text, state):
        return Action(**next(row["action"] for row in fixtures if row["text"] == text))
    async def lookup(constraints):
        await asyncio.sleep(0.2)
        return "Synthetic search: " + json.dumps(constraints, ensure_ascii=False)
    agent = Orchestrator(planner, {"search": lookup}, MemoryPlayback())
    for row in fixtures:
        await agent.accept(row["text"])
        await asyncio.sleep(0.02)
    await agent.drain()
    for event in agent.events:
        print(json.dumps(event, ensure_ascii=False))
    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
