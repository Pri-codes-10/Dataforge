"""Explicit local configuration. Never prints secret values."""
import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("GEMINI_API_KEY", "LLM_MODEL", "DEEPGRAM_API_KEY", "RIME_API_KEY",
            "RIME_MODEL", "RIME_VOICE", "RIME_LANGUAGE")


def load():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)


def missing(room=False):
    names = REQUIRED + (("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET") if room else ())
    return [name for name in names if not os.getenv(name, "").strip()]


def require(room=False):
    absent = missing(room)
    if absent:
        raise ValueError("Missing configuration: " + ", ".join(absent))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check local configuration without contacting providers")
    parser.add_argument("--room", action="store_true", help="Also require LiveKit Cloud/server credentials")
    args = parser.parse_args()
    load()
    absent = missing(args.room)
    for name in REQUIRED + (("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET") if args.room else ()):
        print(f"{name}: {'MISSING' if name in absent else 'set'}")
    print("Configuration only; provider access and language quality are not validated.")
    raise SystemExit(1 if absent else 0)
