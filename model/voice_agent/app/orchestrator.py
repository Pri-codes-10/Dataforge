"""Single-event-loop engine. All output passes through a generation fence.

Playback.submit and stop must be synchronous, nonblocking operations; the real
transport must also reject old generations at the final audio-consumption edge.
"""
import asyncio
import copy
import time
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol
from uuid import uuid4


@dataclass(frozen=True)
class Action:
    kind: Literal["update_state_only", "call_tool", "respond"]
    changes: dict[str, Any] = field(default_factory=dict)
    text: str = ""
    tool: str | None = None
    new_intent: bool = False
    reset_constraints: bool = False

    def validate(self, tools):
        if self.kind not in {"update_state_only", "call_tool", "respond"}:
            raise ValueError("Unknown action")
        if self.kind == "call_tool" and self.tool not in tools:
            raise ValueError("Tool is not registered")
        if self.kind != "call_tool" and self.tool is not None:
            raise ValueError("Only call_tool may specify a tool")
        if not isinstance(self.changes, dict) or not isinstance(self.text, str):
            raise ValueError("Malformed action")


@dataclass
class SessionState:
    session_id: str = field(default_factory=lambda: uuid4().hex)
    generation: int = 0
    constraints: dict = field(default_factory=dict)
    active_tool_calls: dict = field(default_factory=dict)
    history: list = field(default_factory=list)


class Playback(Protocol):
    provider: str
    def submit(self, generation: int, text: str): ...
    def stop(self, generation: int): ...


class Orchestrator:
    def __init__(self, planner, tools, playback: Playback, *, timeout=30, event_sink=None, language="en"):
        self.state = SessionState()
        self.planner, self.tools, self.playback = planner, tools, playback
        self.timeout = timeout
        self.hindi = language in {"hi", "hin"}
        self.events = []
        self._tasks = set()
        self._turn_lock = asyncio.Lock()
        self._closed = False
        self.event_sink = event_sink
        self._input_open = False
        self._input_version = 0
        self._deferred_speech = []

    def begin_input(self, *, barge_in=False):
        """Hold output while listening; status during silent tool work stays valid."""
        self._input_open = True
        self._input_version += 1
        if barge_in or self._turn_lock.locked():
            self.interrupt()

    def finish_input(self):
        self._input_open = False
        pending, self._deferred_speech = self._deferred_speech, []
        for generation, text in pending:
            self._speak(generation, text)

    def log(self, event, **data):
        self.events.append(dict(event=event, timestamp=time.monotonic(),
                                session_id=self.state.session_id,
                                generation=self.state.generation, **data))
        if self.event_sink:
            self.event_sink(self.events[-1])

    def _advance(self, reason):
        self.state.generation += 1
        self.playback.stop(self.state.generation)
        for task in tuple(self._tasks):
            task.cancel()
        self.log("generation_changed", reason=reason)

    def interrupt(self):
        if not self._closed:
            self._advance("barge_in")

    def _speak(self, generation, text):
        if self._closed or generation != self.state.generation:
            self.log("stale_speech_dropped", launched_gen=generation)
            return
        if self._input_open:
            self._deferred_speech.append((generation, text))
            return
        if text:
            self.playback.submit(generation, text)
            self.log("speech_submitted", text=text, provider=self.playback.provider)

    async def accept(self, transcript):
        input_version = self._input_version
        try:
            await self._accept(transcript)
        finally:
            if input_version == self._input_version:
                self.finish_input()

    async def _accept(self, transcript):
        """Accept final raw STT text; serialize planning but never wait for tools.

        The STT/VAD transport calls interrupt() immediately on speech start.
        Planning is serialized to avoid losing deltas from overlapping turns.
        """
        async with self._turn_lock:
            if self._closed:
                raise RuntimeError("Session is closed")
            generation = self.state.generation
            snapshot = copy.deepcopy(self.state.constraints)
            self.log("transcript_received", transcript=transcript)
            try:
                async with asyncio.timeout(self.timeout):
                    if hasattr(self.planner, "plan"):
                        action = await self.planner.plan(transcript, snapshot, {
                            "active_tool_count": sum(g == generation for g in self.state.active_tool_calls.values()),
                            "generation": generation,
                        })
                    else:
                        action = await self.planner(transcript, snapshot)
                action.validate(self.tools)
            except Exception as error:
                self.log("planner_failed", error_type=type(error).__name__, status=getattr(error, "status_code", None))
                self._speak(generation, "माफ़ कीजिए, अनुरोध पूरा नहीं हुआ। कृपया फिर से कोशिश करें।" if self.hindi else "I couldn't understand that request. Please try again.")
                return
            if self._closed or generation != self.state.generation:
                self.log("stale_plan_dropped", launched_gen=generation)
                return
            updated = {} if action.reset_constraints else snapshot
            for key, value in action.changes.items():
                if value is None:
                    updated.pop(key, None)
                else:
                    updated[key] = copy.deepcopy(value)
            if updated != self.state.constraints or action.new_intent or action.reset_constraints:
                self._advance("instruction_changed")
            self.state.constraints = updated
            generation = self.state.generation
            self.state.history.append(dict(transcript=transcript,
                                           changes=copy.deepcopy(action.changes),
                                           generation=generation))
            self._speak(generation, action.text)
            if action.kind == "call_tool":
                call_id = uuid4().hex
                self.state.active_tool_calls[call_id] = generation
                self.log("tool_dispatched", call_id=call_id, tool=action.tool)
                task = asyncio.create_task(self._execute(call_id, generation, action.tool,
                                                        copy.deepcopy(updated)))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)
                task.add_done_callback(lambda _, cid=call_id:
                                       self.state.active_tool_calls.pop(cid, None))

    async def _execute(self, call_id, generation, name, constraints):
        try:
            async with asyncio.timeout(self.timeout):
                result = await self.tools[name](constraints)
            # Wait for a pending instruction's classification before publishing.
            async with self._turn_lock:
                if self._closed or generation != self.state.generation:
                    self.log("stale_result_dropped", call_id=call_id, launched_gen=generation)
                    return
                if not isinstance(result, str):
                    raise ValueError("Tool result must be response text")
                self.log("tool_result_delivered", call_id=call_id)
                self._speak(generation, result)
        except asyncio.CancelledError:
            self.log("tool_cancelled", call_id=call_id, launched_gen=generation)
        except Exception as error:
            self.log("tool_failed", call_id=call_id, error_type=type(error).__name__)
            self._speak(generation, "खोज पूरी नहीं हुई। कृपया फिर से कोशिश करें।" if self.hindi else "The lookup failed. Please try again.")
        finally:
            self.state.active_tool_calls.pop(call_id, None)

    async def drain(self):
        while self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)

    async def close(self):
        self._closed = True
        self._advance("session_closed")
        await self.drain()
