import re
from dataclasses import dataclass


@dataclass
class LanguageResult:
    primary_language: str
    is_code_switched: bool


class LanguageService:

    # Strong Roman-Hindi words.
    # Ambiguous short words such as "to", "aur", "bhi"
    # are deliberately excluded.
    HINDI_WORDS = {
        "mujhe",
        "mujhko",
        "mujhse",
        "mera",
        "meri",
        "mere",
        "hum",
        "hume",
        "humein",
        "hamara",
        "hamari",
        "aap",
        "aapka",
        "aapki",
        "aapko",
        "tum",
        "tumhara",
        "tumhari",
        "tujhe",
        "tera",
        "teri",

        "yeh",
        "yah",
        "woh",
        "voh",

        "kya",
        "kyun",
        "kyon",
        "kaise",
        "kaisa",
        "kaisi",
        "kab",
        "kahan",
        "kahaan",
        "kaun",
        "kitna",
        "kitni",
        "kitne",

        "hai",
        "hain",
        "ho",
        "tha",
        "thi",
        "the",
        "hoga",
        "hogi",
        "honge",

        "kar",
        "karo",
        "karna",
        "karni",
        "karta",
        "karti",
        "karte",
        "kiya",
        "kiye",

        "diya",
        "diye",
        "dena",
        "lena",
        "chahiye",

        "chahta",
        "chahti",

        "jaana",
        "jana",
        "jao",
        "aana",
        "ana",
        "aao",
        "gaya",
        "gayi",

        "raha",
        "rahi",
        "rahe",

        "wala",
        "wali",
        "wale",

        "abhi",
        "aaj",
        "kal",
        "subah",
        "shaam",
        "raat",

        "bahut",
        "thoda",
        "thodi",
        "sab",
        "kuch",

        "nahi",
        "nahin",
        "mat",

        "kyunki",
        "agar",
        "phir",

        "sirf",
        "yahan",
        "wahan",
        "andar",
        "bahar",
        "upar",
        "neeche",
        "pehle",
        "baad",
        "ab",
    }

    # Strong English indicators.
    ENGLISH_WORDS = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "am",
        "be",
        "been",
        "being",

        "find",
        "show",
        "give",
        "get",
        "book",
        "cancel",
        "change",
        "check",
        "search",

        "want",
        "need",
        "would",
        "could",
        "should",
        "please",
        "help",
        "tell",
        "make",

        "flight",
        "flights",
        "train",
        "trains",
        "bus",
        "buses",
        "hotel",
        "hotels",
        "ticket",
        "tickets",

        "tomorrow",
        "today",
        "yesterday",
        "morning",
        "evening",
        "night",
        "afternoon",

        "from",
        "to",
        "for",
        "with",
        "without",
        "at",
        "on",
        "in",
        "by",
    }

    # Names/places should not affect language detection.
    PROPER_NOUNS = {
        "delhi",
        "mumbai",
        "kolkata",
        "india",
        "indian",
        "bangalore",
        "bengaluru",
        "chennai",
        "hyderabad",
        "pune",
    }

    def detect(self, text: str) -> LanguageResult:

        if not text or not text.strip():
            return LanguageResult(
                primary_language="unknown",
                is_code_switched=False,
            )

        text = text.strip()

        # -----------------------------------------------
        # Devanagari detection
        # -----------------------------------------------

        devanagari_chars = len(
            re.findall(r"[\u0900-\u097F]", text)
        )

        latin_chars = len(
            re.findall(r"[A-Za-z]", text)
        )

        if devanagari_chars > 0:

            if latin_chars > 0:
                return LanguageResult(
                    primary_language="mixed",
                    is_code_switched=True,
                )

            return LanguageResult(
                primary_language="hi",
                is_code_switched=False,
            )

        # -----------------------------------------------
        # Roman-script detection
        # -----------------------------------------------

        words = re.findall(
            r"[A-Za-z]+",
            text.lower(),
        )

        if not words:
            return LanguageResult(
                primary_language="unknown",
                is_code_switched=False,
            )

        # Ignore proper nouns when calculating language.
        analysis_words = [
            word
            for word in words
            if word not in self.PROPER_NOUNS
        ]

        hindi_matches = [
            word
            for word in analysis_words
            if word in self.HINDI_WORDS
        ]

        english_matches = [
            word
            for word in analysis_words
            if word in self.ENGLISH_WORDS
        ]

        hindi_count = len(hindi_matches)
        english_count = len(english_matches)

        # -----------------------------------------------
        # Mixed Hindi + English
        # -----------------------------------------------

        if hindi_count >= 1 and english_count >= 1:
            return LanguageResult(
                primary_language="mixed",
                is_code_switched=True,
            )

        # -----------------------------------------------
        # Hindi
        # -----------------------------------------------

        if hindi_count >= 2:
            return LanguageResult(
                primary_language="hi",
                is_code_switched=False,
            )

        # -----------------------------------------------
        # English
        # -----------------------------------------------

        return LanguageResult(
            primary_language="en",
            is_code_switched=False,
        )


language_service = LanguageService()