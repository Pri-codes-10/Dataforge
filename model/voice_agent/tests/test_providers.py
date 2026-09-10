import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from app.inventory import FlightSearch
from app.live_playback import LiveKitPlayback

try:
    from app.planner import Plan, OpenAIPlanner
except ImportError:
    Plan = None


@unittest.skipIf(Plan is None, "Install requirements.txt to run planner tests")
class PlannerTests(unittest.IsolatedAsyncioTestCase):
    def plan(self, changes=None, **kwargs):
        return Plan(kind="call_tool", changes=changes or [], text="Checking.",
                    tool="search", new_intent=False, reset_constraints=False, **kwargs)

    async def test_raw_mixed_transcript_and_state_reach_provider(self):
        response = SimpleNamespace(output_parsed=self.plan([{"key":"max_price", "value":6000}]))
        parse = AsyncMock(return_value=response)
        planner = OpenAIPlanner(SimpleNamespace(responses=SimpleNamespace(parse=parse)), "configured-model")
        text = "छह हजार se kam"
        action = await planner.plan(text, {"destination":"Delhi"}, {"active_tool_count":1})
        payload = json.loads(parse.call_args.kwargs["input"][1]["content"])
        self.assertEqual(payload["transcript"], text)
        self.assertEqual(payload["constraints"], {"destination":"Delhi"})
        self.assertEqual(action.changes, {"max_price":6000})
        self.assertFalse(parse.call_args.kwargs["store"])

    async def test_refusal_is_not_an_action(self):
        planner = OpenAIPlanner(SimpleNamespace(responses=SimpleNamespace(
            parse=AsyncMock(return_value=SimpleNamespace(output_parsed=None)))), "configured-model")
        with self.assertRaises(ValueError):
            await planner.plan("hello", {}, {})

    async def test_budget_boolean_is_rejected(self):
        with self.assertRaises(ValueError):
            self.plan([{"key":"max_price", "value":True}]).to_action()

    async def test_duplicate_deltas_are_rejected(self):
        with self.assertRaises(ValueError):
            self.plan([{"key":"destination", "value":"Delhi"},
                       {"key":"destination", "value":"Mumbai"}]).to_action()


class InventoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_hindi_result_matches_selected_voice(self):
        result = await FlightSearch(0, "hi")({"origin":"Kolkata", "destination":"Delhi",
            "date":"Saturday", "max_price":6000, "nonstop":True})
        self.assertIn("5400", result)
        self.assertIn("कोई बुकिंग नहीं हुई", result)
        self.assertNotIn("Delhi", result)

    async def test_filters_budget_and_nonstop(self):
        result = await FlightSearch(0)({"origin":"Kolkata", "destination":"Delhi",
                                      "date":"Saturday", "max_price":6000, "nonstop":True})
        self.assertIn("5400", result)
        self.assertIn("Nothing is booked", result)

    async def test_budget_boundary_is_exclusive(self):
        result = await FlightSearch(0)({"origin":"Kolkata", "destination":"Delhi",
                                      "date":"Saturday", "max_price":5400, "nonstop":True})
        self.assertIn("No synthetic flights", result)

    async def test_lookup_is_cancellable(self):
        task = asyncio.create_task(FlightSearch(20)({}))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task


class FakeHandle:
    def __init__(self):
        self.interrupted = False
        self.callback = None
    def add_done_callback(self, callback):
        self.callback = callback
    def interrupt(self):
        self.interrupted = True


class PlaybackTests(unittest.TestCase):
    def test_interrupts_all_handles_and_blocks_old_generation(self):
        handles = []
        def say(*args, **kwargs):
            handle = FakeHandle()
            handles.append(handle)
            return handle
        stopped = []
        session = SimpleNamespace(say=say, interrupt=lambda: stopped.append(True))
        playback = LiveKitPlayback(session)
        playback.submit(0, "first")
        playback.submit(0, "second")
        playback.stop(1)
        playback.submit(0, "late")
        self.assertEqual(len(handles), 2)
        self.assertTrue(all(handle.interrupted for handle in handles))
        self.assertTrue(stopped)
        playback.submit(1, "current")
        self.assertEqual(len(handles), 3)
