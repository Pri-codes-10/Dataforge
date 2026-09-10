"""Run from repository root: python -m bench.run_tests."""
import csv
import unittest
from pathlib import Path


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rows = []
    def addSuccess(self, test):
        super().addSuccess(test)
        self.rows.append((test.id(), "PASS", "offline_simulation"))
    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.rows.append((test.id(), "FAIL", "offline_simulation"))
    def addError(self, test, error):
        super().addError(test, error)
        self.rows.append((test.id(), "ERROR", "offline_simulation"))
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.rows.append((test.id(), "SKIP", "offline_simulation"))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover("tests")
    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
    Path("bench/results").mkdir(exist_ok=True)
    with open("bench/results/acceptance.csv", "w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("test", "result", "mode"))
        writer.writerows(result.rows)
    raise SystemExit(not result.wasSuccessful())
