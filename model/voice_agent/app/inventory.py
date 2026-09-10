"""Cancellable lookup of explicitly synthetic flight inventory."""
import asyncio
import json
from .config import ROOT


class FlightSearch:
    def __init__(self, delay=4, language="en"):
        if not 0 <= delay <= 20:
            raise ValueError("Demo delay must be between 0 and 20 seconds")
        self.delay = delay
        self.hindi = language in {"hi", "hin"}
        self.rows = json.loads((ROOT / "fixtures/flights.json").read_text(encoding="utf-8"))

    async def __call__(self, constraints):
        await asyncio.sleep(self.delay)
        if not all(constraints.get(key) for key in ("origin", "destination", "date")):
            if self.hindi:
                return "कृपया प्रस्थान का शहर, गंतव्य और यात्रा का दिन बताइए।"
            return "Please specify the departure city, destination and day for the demo search."
        matches = [row for row in self.rows
                   if all(row[key].casefold() == str(constraints[key]).casefold()
                          for key in ("origin", "destination", "date"))
                   and row["price"] < constraints.get("max_price", float("inf"))
                   and (not constraints.get("nonstop") or row["nonstop"])]
        if not matches:
            if self.hindi:
                return "इस काल्पनिक सूची में आपकी शर्तों से मेल खाती उड़ान नहीं मिली। यह वास्तविक किरायों की खोज नहीं है।"
            return "No synthetic flights match those constraints. This demo does not search real fares."
        best = min(matches, key=lambda row: row["price"])
        if self.hindi:
            names = {"Kolkata":"कोलकाता", "Delhi":"दिल्ली", "Mumbai":"मुंबई", "Saturday":"शनिवार", "Sunday":"रविवार"}
            return (f"इस काल्पनिक सूची में {names[best['origin']]} से {names[best['destination']]} की "
                    f"{names[best['date']]} की उड़ान {best['price']} रुपये की है। "
                    f"{'यह सीधी उड़ान है।' if best['nonstop'] else 'रास्ते में एक ठहराव है।'} कोई बुकिंग नहीं हुई है।")
        return (f"In the synthetic demo inventory, {best['origin']} to {best['destination']} "
                f"on {best['date']} is {best['price']} rupees, "
                f"{'nonstop' if best['nonstop'] else 'with one stop'}. Nothing is booked.")
