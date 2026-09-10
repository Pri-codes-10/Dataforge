"""Small real provider checks. Prints status only; never prints credentials."""
import asyncio
import os
from app.config import load, require


async def main():
    import aiohttp
    from livekit.plugins import rime
    from app.gemini_planner import GeminiPlanner
    load()
    require()
    passed = True
    async with aiohttp.ClientSession() as client:
        try:
            action = await GeminiPlanner(client, os.environ["LLM_MODEL"], os.environ["GEMINI_API_KEY"], os.environ["RIME_LANGUAGE"]).plan(
                "Kolkata se Delhi Saturday flights dekho, budget chhe hazaar se kam.", {},
                {"active_tool_count": 0, "generation": 0})
            expected = {"origin":"Kolkata", "destination":"Delhi", "date":"Saturday", "max_price":6000}
            valid = action.kind == "call_tool" and all(action.changes.get(k) == v for k, v in expected.items())
            print("Gemini mixed-text planner:", "PASS" if valid else "FAIL (unexpected action)")
            passed &= valid
        except Exception as error:
            print("Gemini planner: FAIL", type(error).__name__, "status", getattr(error, "status_code", None),
                  "code", getattr(error, "code", None))
            passed = False
    async with aiohttp.ClientSession() as http:
        tts = rime.TTS(api_key=os.environ["RIME_API_KEY"], model=os.environ["RIME_MODEL"],
                       speaker=os.environ["RIME_VOICE"], lang=os.environ["RIME_LANGUAGE"],
                       use_websocket=False, base_url=os.getenv("RIME_HTTP_URL", "https://users.rime.ai/v1/rime-tts"),
                       sample_rate=24000, http_session=http)
        try:
            samples = 0
            async with asyncio.timeout(30):
                async with tts.synthesize("नमस्ते। यह आवाज़ की जाँच है।" if os.environ["RIME_LANGUAGE"] in {"hi", "hin"} else "Hello. This is a voice test.") as stream:
                    async for event in stream:
                        samples += event.frame.samples_per_channel
            print("Rime streaming audio:", "PASS" if samples else "FAIL (empty audio)")
            passed &= samples > 0
        except Exception as error:
            print("Rime streaming audio: FAIL", type(error).__name__)
            passed = False
        finally:
            await tts.aclose()
    print("This check does not play audio; microphone accuracy and audible latency remain untested.")
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(main()) else 1)
