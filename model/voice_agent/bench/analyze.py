"""Summarize tests without claiming audible latency."""
import csv
from collections import Counter
from pathlib import Path

if __name__ == "__main__":
    with (Path(__file__).parent / "results/acceptance.csv").open(encoding="utf-8") as stream:
        counts = Counter(row["result"] for row in csv.DictReader(stream))
    print("Offline simulation results:", dict(counts))
    print("Live STT accuracy, audible stale output, and cold/cached audible latency: NOT MEASURED")
