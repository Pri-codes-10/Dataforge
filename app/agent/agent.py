import httpx
from typing import Dict, List, Optional

from app.core.config import settings
from app.agent.state import ConversationState, conversation_state as default_state


class VoiceAgent:
    """
    LLM agent for the SUTRA conversational voice assistant.

    Handles:
    - Conversational spoken language generation (short, punchy, human-like)
    - Natural English, Hindi, Hinglish code-switching, and Bengali
    - Context continuity and task constraint tracking
    - Real tool result summarization for speech
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
        state: Optional[ConversationState] = None,
        messages_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Generate a spoken response using conversation state and real tool results.
        """
        active_state = state or default_state

        # Update language information
        active_state.update_language(
            language=language,
            is_code_switched=(language == "mixed"),
        )

        api_key = settings.SARVAM_API_KEY or self.api_key

        if not api_key:
            assistant_text = (
                f"I heard you: '{user_text}'. Note: Please set SARVAM_API_KEY in your .env file."
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
                "content": self._system_prompt(language, tool_result, active_state),
            }
        ]

        # Include conversation history (passed explicitly or from active state)
        if messages_history is not None:
            messages.extend(messages_history)
        else:
            messages.extend(active_state.get_messages())

        try:
            response = await self.client.post(
                self.api_url,
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.4,
                    "reasoning_effort": None,
                },
                timeout=15.0,
            )
            response.raise_for_status()
            response_data = response.json()

            assistant_text = (
                response_data["choices"][0]["message"].get("content") or ""
            ).strip()
        except Exception:
            # Natural conversational fallback based on language and constraints
            constraints_str = ", ".join(f"{k}: {v}" for k, v in active_state.constraints.items()) or "your request"
            if tool_result:
                if language in ["hi", "mixed"]:
                    assistant_text = f"Theek hai, information mil gayi: {tool_result[:100]}."
                elif language == "bn":
                    assistant_text = f"Thik achhe, tothyo paowa gechhe: {tool_result[:100]}."
                else:
                    assistant_text = f"Here's what I found: {tool_result[:100]}."
            else:
                if language in ["hi", "mixed"]:
                    assistant_text = f"Samajh gaya. Aapka update ho gaya hai ({constraints_str})."
                elif language == "bn":
                    assistant_text = f"Bujhte perechhi. Apnar request update hoyechhe ({constraints_str})."
                else:
                    assistant_text = f"Got it, I've updated your request for {constraints_str}."

        return assistant_text

    def _system_prompt(self, language: str, tool_result: str = "", state: Optional[ConversationState] = None) -> str:
        active_state = state or default_state
        constraints_desc = ", ".join(f"{k}='{v}'" for k, v in active_state.constraints.items()) or "None"
        tool_desc = f"Latest Real Tool Result: {tool_result}" if tool_result else "No external tool required or executed."

        lang_instruction = {
            "hi": "The user speaks Hindi. You MUST respond in natural conversational Hindi or Hinglish (Roman script or Devanagari). Do NOT answer in English only.",
            "bn": "The user speaks Bengali. You MUST respond in natural Bengali (e.g. 'আপনার ফ্লাইট বা তথ্য পেয়ে গেছি।'). Do NOT answer in English only.",
            "mixed": "The user speaks code-switched Hinglish (Hindi + English). Respond in natural conversational Hinglish (e.g. 'Theek hai, I found three options for Saturday under 6000 rupees.').",
            "en": "The user speaks English. Respond in fluent, natural, conversational English.",
        }.get(language, "Respond in the language the user used.")

        return f"""
You are SUTRA, an advanced realtime conversational voice assistant.
Your words will be directly converted to speech by Rime TTS and spoken aloud to the user.

Current Language: {language}
{lang_instruction}

Active Task Constraints:
{constraints_desc}

{tool_desc}

CRITICAL SPOKEN CONVERSATION RULES:
1. Speak strictly for the ear, NOT for reading:
   - 1 or 2 concise, spoken sentences maximum.
   - Use natural contractions in English ('I'll', 'I'm', 'there's', 'you'd', 'we've').
   - Use natural acknowledgements ('Sure', 'Got it', 'Yeah', 'Theek hai', 'All right').
2. Zero written formatting:
   - NEVER use bullet points, numbered lists, markdown, headings, bold, asterisks, or JSON.
   - NEVER say "According to the API...", "I have successfully completed...", "As an AI...".
   - NEVER repeat the user's entire prompt back to them.
3. Incorporating Tool Results:
   - If real tool results are provided above, speak the key finding naturally and directly (e.g. "Yeah, I found three flights for Saturday. The cheapest is around five thousand eight hundred rupees.").
   - If a tool indicates an error or that a service is unavailable, inform the user politely and naturally without technical jargon (e.g. "Sorry, flight search is unavailable right now.").
4. Natural pacing:
   - Use normal punctuation (commas, periods) to create realistic pauses. Avoid artificial ellipses.
"""


agent = VoiceAgent()