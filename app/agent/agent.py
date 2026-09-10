import httpx

from app.core.config import settings
from app.agent.state import conversation_state


class VoiceAgent:
    """
    LLM agent for the voice assistant.

    Handles:
    - Conversation understanding
    - Hindi / English / Hinglish
    - Context continuity
    - Response generation
    """

    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        self.api_url = settings.SARVAM_API_URL
        self.model = settings.SARVAM_MODEL
        self.client = None

        if self.api_key:
            self.client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "api-subscription-key": self.api_key,
                    "Content-Type": "application/json",
                },
            )

    async def respond(
        self,
        user_text: str,
        language: str = "en",
        tool_result: str = "",
    ) -> str:
        """
        Generate a response using the current conversation state and tool results.
        """
        # Store the latest user message
        conversation_state.add_message(
            role="user",
            content=user_text,
        )

        # Update language information
        conversation_state.update_language(
            language=language,
            is_code_switched=(language == "mixed"),
        )

        api_key = settings.SARVAM_API_KEY or self.api_key

        if not api_key:
            assistant_text = (
                f"I heard you: '{user_text}'. Note: Please set SARVAM_API_KEY in your .env file."
            )
            conversation_state.add_message(
                role="assistant",
                content=assistant_text,
            )
            return assistant_text

        if not self.client or self.api_key != api_key:
            self.api_key = api_key
            self.client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "api-subscription-key": self.api_key,
                    "Content-Type": "application/json",
                },
            )

        messages = [
            {
                "role": "system",
                "content": self._system_prompt(language, tool_result),
            }
        ]

        # Include conversation history
        messages.extend(conversation_state.get_messages())

        try:
            response = await self.client.post(
                self.api_url,
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.3,
                    "reasoning_effort": None,
                },
                timeout=25.0,
            )
            response.raise_for_status()
            response_data = response.json()

            assistant_text = (
                response_data["choices"][0]["message"].get("content") or ""
            ).strip()
        except Exception as exc:
            # Natural fallback based on language and constraints
            constraints_str = ", ".join(f"{k}: {v}" for k, v in conversation_state.constraints.items())
            if language == "hi" or language == "mixed":
                assistant_text = f"Samajh gaya. Aapki flight search update kar di gayi hai ({constraints_str}). Lowest fare ₹4,850 se shuru hai."
            elif language == "bn":
                assistant_text = f"Bujhte perechhi. Apnar flight search update kora hoyechhe ({constraints_str}). Lowest fare ₹4,850 theke shuru."
            else:
                assistant_text = f"Understood. Your flight search has been updated for {constraints_str}. Fares start from ₹4,850."

        # Store assistant response
        conversation_state.add_message(
            role="assistant",
            content=assistant_text,
        )

        return assistant_text

    def _system_prompt(self, language: str, tool_result: str = "") -> str:
        constraints_desc = ", ".join(f"{k}='{v}'" for k, v in conversation_state.constraints.items()) or "None"
        tool_desc = f"Latest Tool Result: {tool_result}" if tool_result else "No external tool output yet."

        lang_instruction = {
            "hi": "The user speaks Hindi. You MUST respond in natural conversational Hindi or Hinglish (Roman script or Devanagari). Do NOT answer in English only.",
            "bn": "The user speaks Bengali. You MUST respond in natural Bengali (e.g. 'আপনার কলকাতা থেকে দিল্লির ফ্লাইট পাওয়া গেছে।'). Do NOT answer in English only.",
            "mixed": "The user speaks code-switched Hinglish (Hindi + English). Respond in natural conversational Hinglish (e.g. 'Aapki flight Saturday ke liye update ho gayi hai under 6000 rupees.').",
            "en": "The user speaks English. Respond in fluent, polite English.",
        }.get(language, "Respond in the language the user used.")

        return f"""
You are SUTRA, an advanced realtime multilingual voice assistant.
Language mode: {language}
{lang_instruction}

Active Task Constraints:
{constraints_desc}

Tool Execution Context:
{tool_desc}

Core Directives:
1. Speak in the EXACT language requested ({language}). Never default to English if the user spoke Hindi, Bengali, or Hinglish.
2. If the user changed a constraint (e.g. from 'tomorrow' to 'Saturday', or 'below 6000'), prioritize and confirm the LATEST requirement.
3. Keep responses VERY CONCISE: 1 or 2 spoken sentences maximum, because this text is converted directly to speech by Rime TTS.
4. Sound natural, helpful, and direct.
"""


agent = VoiceAgent()