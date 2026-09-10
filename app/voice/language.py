import re
from dataclasses import dataclass


@dataclass
class LanguageResult:
    primary_language: str
    is_code_switched: bool
    languages: list
    label: str


class LanguageService:

    # Strong Roman-Hindi words.
    HINDI_WORDS = {
        "mujhe", "mujhko", "mujhse", "mera", "meri", "mere",
        "hum", "hume", "humein", "hamara", "hamari",
        "aap", "aapka", "aapki", "aapko", "tum", "tumhara", "tumhari",
        "tujhe", "tera", "teri", "yeh", "yah", "woh", "voh",
        "kya", "kyun", "kyon", "kaise", "kaisa", "kaisi",
        "kab", "kahan", "kahaan", "kaun", "kitna", "kitni", "kitne",
        "hai", "hain", "ho", "tha", "thi", "the", "hoga", "hogi", "honge",
        "kar", "karo", "karna", "karni", "karta", "karti", "karte", "kiya", "kiye",
        "diya", "diye", "dena", "lena", "chahiye", "chahta", "chahti",
        "jaana", "jana", "jao", "aana", "ana", "aao", "gaya", "gayi",
        "raha", "rahi", "rahe", "wala", "wali", "wale",
        "abhi", "aaj", "kal", "subah", "shaam", "raat",
        "bahut", "thoda", "thodi", "sab", "kuch",
        "nahi", "nahin", "mat", "kyunki", "agar", "phir",
        "sirf", "yahan", "wahan", "andar", "bahar", "upar", "neeche", "pehle", "baad", "ab",
        "rupaye", "rupees", "hazaar", "hazar", "kam", "jyada", "zyada", "chahiye", "shanivar", "ravivar",
    }

    # Strong Roman-Bengali words.
    BENGALI_WORDS = {
        "amar", "amake", "amader", "tumi", "tomar", "tomake", "apni", "apnar",
        "apnake", "theke", "chai", "chao", "chawa", "dorkar", "lagbe",
        "kothay", "kobe", "ki", "koto", "korbo", "korun", "koren",
        "ekta", "duto", "shani", "shonibar", "agami", "kal", "aj",
        "achhe", "nei", "na", "dhonnobad", "taka", "bhalo", "khub",
        "ekhane", "sekhane", "jabo", "jete",
    }

    # Strong English indicators.
    ENGLISH_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "am", "be", "been", "being",
        "find", "show", "give", "get", "book", "cancel", "change", "check", "search",
        "want", "need", "would", "could", "should", "please", "help", "tell", "make",
        "flight", "flights", "train", "trains", "bus", "buses", "hotel", "hotels", "ticket", "tickets",
        "tomorrow", "today", "yesterday", "morning", "evening", "night", "afternoon", "saturday", "sunday",
        "from", "to", "for", "with", "without", "at", "on", "in", "by", "under", "below", "thousand",
    }

    # Names/places should not affect language detection.
    PROPER_NOUNS = {
        "delhi", "mumbai", "kolkata", "india", "indian",
        "bangalore", "bengaluru", "chennai", "hyderabad", "pune",
    }

    def detect(self, text: str, stt_lang_code: str = "") -> LanguageResult:
        if not text or not text.strip():
            return LanguageResult(
                primary_language="unknown",
                is_code_switched=False,
                languages=["Unknown"],
                label="Unknown",
            )

        text = text.strip()

        # -----------------------------------------------
        # Bengali Script detection [\u0980-\u09FF]
        # -----------------------------------------------
        bengali_chars = len(re.findall(r"[\u0980-\u09FF]", text))
        latin_chars = len(re.findall(r"[A-Za-z]", text))
        devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text))

        if bengali_chars > 0:
            if latin_chars > 2:
                return LanguageResult(
                    primary_language="mixed",
                    is_code_switched=True,
                    languages=["Bengali", "English"],
                    label="Bengali + English",
                )
            return LanguageResult(
                primary_language="bn",
                is_code_switched=False,
                languages=["Bengali"],
                label="Bengali",
            )

        # -----------------------------------------------
        # Devanagari detection [\u0900-\u097F]
        # -----------------------------------------------
        if devanagari_chars > 0:
            if latin_chars > 2:
                return LanguageResult(
                    primary_language="mixed",
                    is_code_switched=True,
                    languages=["Hindi", "English"],
                    label="Hindi + English",
                )
            return LanguageResult(
                primary_language="hi",
                is_code_switched=False,
                languages=["Hindi"],
                label="Hindi",
            )

        # -----------------------------------------------
        # Roman-script analysis
        # -----------------------------------------------
        words = re.findall(r"[A-Za-z]+", text.lower())
        if not words:
            if "bn" in stt_lang_code:
                return LanguageResult("bn", False, ["Bengali"], "Bengali")
            if "hi" in stt_lang_code:
                return LanguageResult("hi", False, ["Hindi"], "Hindi")
            return LanguageResult("en", False, ["English"], "English")

        analysis_words = [w for w in words if w not in self.PROPER_NOUNS]

        hindi_matches = [w for w in analysis_words if w in self.HINDI_WORDS]
        bengali_matches = [w for w in analysis_words if w in self.BENGALI_WORDS]
        english_matches = [w for w in analysis_words if w in self.ENGLISH_WORDS]

        hindi_count = len(hindi_matches)
        bengali_count = len(bengali_matches)
        english_count = len(english_matches)

        # Consider STT metadata
        if "bn" in stt_lang_code and bengali_count >= 1:
            if english_count >= 1:
                return LanguageResult("mixed", True, ["Bengali", "English"], "Bengali + English")
            return LanguageResult("bn", False, ["Bengali"], "Bengali")

        if "hi" in stt_lang_code:
            if hindi_count >= 1 and english_count >= 1:
                return LanguageResult("mixed", True, ["Hindi", "English"], "Hindi + English")
            if hindi_count >= 1 or english_count == 0:
                return LanguageResult("hi", False, ["Hindi"], "Hindi")

        # Mixed Bengali + English
        if bengali_count >= 1 and english_count >= 1:
            return LanguageResult(
                primary_language="mixed",
                is_code_switched=True,
                languages=["Bengali", "English"],
                label="Bengali + English",
            )

        if bengali_count >= 2:
            return LanguageResult(
                primary_language="bn",
                is_code_switched=False,
                languages=["Bengali"],
                label="Bengali",
            )

        # Mixed Hindi + English
        if hindi_count >= 1 and english_count >= 1:
            return LanguageResult(
                primary_language="mixed",
                is_code_switched=True,
                languages=["Hindi", "English"],
                label="Hindi + English",
            )

        # Pure Hindi
        if hindi_count >= 1:
            return LanguageResult(
                primary_language="hi",
                is_code_switched=False,
                languages=["Hindi"],
                label="Hindi",
            )

        # Default English
        return LanguageResult(
            primary_language="en",
            is_code_switched=False,
            languages=["English"],
            label="English",
        )


language_service = LanguageService()