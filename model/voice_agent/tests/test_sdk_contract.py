import unittest
try:
    from livekit.agents import AgentSession
    from livekit.plugins import rime, deepgram
except ImportError:
    AgentSession = None


@unittest.skipIf(AgentSession is None, "Install voice dependencies")
class SDKContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_installed_plugins_construct_without_remote_calls(self):
        tts = rime.TTS(api_key="offline-test-placeholder", model="coda", speaker="astra",
                       lang="eng", sample_rate=24000, use_websocket=True,
                       base_url="wss://users-ws.rime.ai")
        stt = deepgram.STT(api_key="offline-test-placeholder", model="nova-3", language="multi")
        session = AgentSession(stt=stt, tts=tts,
            turn_handling={"turn_detection":"vad", "interruption":{"mode":"vad",
                          "resume_false_interruption":False},
                          "preemptive_generation":{"enabled":False}})
        self.assertTrue(tts.capabilities.streaming)
        self.assertEqual(tts.sample_rate, 24000)
        self.assertEqual(session.turn_detection, "vad")
        await tts.aclose()
        await stt.aclose()
