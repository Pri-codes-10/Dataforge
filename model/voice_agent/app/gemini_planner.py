"""Gemini REST structured-output adapter; reuses the validated action contract."""
import json
import re
import aiohttp
from .planner import Plan, SYSTEM


class GeminiError(RuntimeError):
    def __init__(self, status):
        self.status_code = status
        super().__init__(f"Gemini request failed (HTTP {status})")


class GeminiPlanner:
    def __init__(self, client, model, api_key, language="en"):
        if not re.fullmatch(r"gemini-[a-zA-Z0-9._-]+", model):
            raise ValueError("LLM_MODEL must be a Gemini model ID")
        self.client, self.model, self.api_key = client, model, api_key
        self.language = language

    async def plan(self, transcript, constraints, context):
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM + (
                "\nFor the text field, use concise Hindi in Devanagari, matching the configured Hindi voice. Keep structured city/date values in English."
                if self.language in {"hi", "hin"} else "\nUse concise English for the spoken text field.")}]},
            "contents": [{"role": "user", "parts": [{"text": json.dumps({
                "transcript": transcript, "constraints": constraints, "context": context}, ensure_ascii=False)}]}],
            "generationConfig": {"responseMimeType": "application/json",
                                 "responseJsonSchema": Plan.model_json_schema()},
        }
        async with self.client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key}, json=payload,
            timeout=aiohttp.ClientTimeout(total=20), allow_redirects=False,
        ) as response:
            if response.status != 200:
                raise GeminiError(response.status)
            data = await response.json()
        candidates = data.get("candidates", [])
        if not candidates or candidates[0].get("finishReason") != "STOP":
            raise ValueError("Gemini returned blocked or incomplete output")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts if not part.get("thought"))
        return Plan.model_validate_json(text).to_action()
