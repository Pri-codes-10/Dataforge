import asyncio
import unittest
from app.orchestrator import Action, Orchestrator
from app.playback import MemoryPlayback


class ContinuityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.actions = {}
        self.playback = MemoryPlayback()
        async def planner(text, state):
            return self.actions[text]
        async def search(state):
            await asyncio.sleep(0)
            return str(state)
        self.agent = Orchestrator(planner, {"search": search}, self.playback)

    async def asyncTearDown(self):
        await self.agent.close()

    async def send(self, transcript, **kwargs):
        self.actions[transcript] = Action(**kwargs)
        await self.agent.accept(transcript)

    async def test_1_normal_turn(self):
        await self.send("Delhi chalo", kind="call_tool", tool="search", changes={"destination":"Delhi"})
        await self.agent.drain()
        self.assertIn("Delhi", self.playback.consume())

    async def test_2_code_switch_retains_structured_deltas(self):
        await self.send("Saturday Delhi", kind="update_state_only", changes={"destination":"Delhi", "date":"Saturday"})
        await self.send("chhe hazaar", kind="call_tool", tool="search", changes={"max_price":6000})
        await self.agent.drain()
        self.assertEqual(self.agent.state.constraints, {"destination":"Delhi", "date":"Saturday", "max_price":6000})

    async def test_3_constraint_change_cancels_running_tool(self):
        started = asyncio.Event()
        async def slow(state):
            started.set()
            await asyncio.Event().wait()
        self.agent.tools["search"] = slow
        await self.send("first", kind="call_tool", tool="search", changes={"max_price":9000})
        await started.wait()
        await self.send("cheaper", kind="update_state_only", changes={"max_price":6000})
        await self.agent.drain()
        self.assertTrue(any(e["event"] == "tool_cancelled" for e in self.agent.events))
        self.assertFalse(self.playback.submitted)

    async def test_4_uncooperative_stale_result_is_dropped(self):
        started = asyncio.Event()
        async def stubborn(state):
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                return "OUTDATED RESULT"
        self.agent.tools["search"] = stubborn
        await self.send("first", kind="call_tool", tool="search", changes={"destination":"Delhi"})
        await started.wait()
        await self.send("changed", kind="update_state_only", changes={"destination":"Mumbai"})
        await self.agent.drain()
        self.assertTrue(any(e["event"] == "stale_result_dropped" for e in self.agent.events))
        self.assertFalse(self.playback.submitted)

    async def test_5_barge_in_clears_queue_and_rejects_late_audio(self):
        await self.send("hello", kind="respond", text="Old queued sentence")
        old = self.agent.state.generation
        self.agent.interrupt()
        self.playback.submit(old, "Late old audio")
        self.assertIsNone(self.playback.consume())

    async def test_status_does_not_bump_generation(self):
        await self.send("search", kind="update_state_only", changes={"date":"Saturday"})
        generation = self.agent.state.generation
        await self.send("status", kind="respond", text="Still checking")
        self.assertEqual(generation, self.agent.state.generation)

    async def test_interrupt_fences_pending_planner(self):
        started, release = asyncio.Event(), asyncio.Event()
        async def slow(text, state):
            started.set()
            await release.wait()
            return Action("respond", text="Outdated plan")
        self.agent.planner = slow
        task = asyncio.create_task(self.agent.accept("hello"))
        await started.wait()
        self.agent.interrupt()
        release.set()
        await task
        self.assertFalse(self.playback.submitted)

    async def test_invalid_tool_cannot_mutate_state(self):
        await self.send("bad", kind="call_tool", tool="unregistered", changes={"date":"wrong"})
        self.assertEqual(self.agent.state.constraints, {})

    async def test_remove_constraint(self):
        await self.send("add", kind="update_state_only", changes={"max_price":6000})
        await self.send("remove", kind="update_state_only", changes={"max_price":None})
        self.assertEqual(self.agent.state.constraints, {})

    async def test_silent_lookup_survives_status_speech(self):
        started, release = asyncio.Event(), asyncio.Event()
        async def search(state):
            started.set()
            await release.wait()
            return "Current result"
        self.agent.tools["search"] = search
        await self.send("lookup", kind="call_tool", tool="search", changes={"destination":"Delhi"})
        await started.wait()
        generation = self.agent.state.generation
        self.agent.begin_input()
        release.set()
        await self.agent.drain()
        self.assertFalse(self.playback.submitted)
        await self.send("status", kind="respond", text="Here is the update.")
        self.assertEqual(generation, self.agent.state.generation)
        self.assertIn((generation, "Current result"), self.playback.submitted)

    async def test_deferred_result_dropped_after_spoken_correction(self):
        self.agent.begin_input()
        self.agent._speak(0, "Old result held during speech")
        await self.send("correction", kind="update_state_only", changes={"destination":"Mumbai"})
        self.assertFalse(self.playback.submitted)
