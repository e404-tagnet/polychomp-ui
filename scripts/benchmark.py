#!/usr/bin/env python3
"""Benchmark PRISM bias detection latency and accuracy."""
import time, sys
from pathlib import Path

PRISM = Path(__file__).resolve().parent.parent / ".." / "prism-scaffold" / "src"
sys.path.insert(0, str(PRISM))

from prism.classifiers.keyword import classify, dominant

TEST_CASES = [
    ("authority", "What is the official recommendation from the industry standard?"),
    ("confirmation", "Can you confirm that this proves my initial assumption?"),
    ("sunk_cost", "We already spent fifteen thousand, we can not quit now."),
    ("anchoring", "The first price shaped my thinking about this."),
    ("bandwagon", "The whole department knows there is no problem here."),
    ("blind_spot", "Let us ignore her views, she is biased."),
    ("stereotyping", "Dave from tech is worried, but frankly the tech team are always pessimists."),
    ("status_quo", "If it is not broke, do not fix it."),
]

print("Bias Benchmark")
print("=" * 50)
total = 0
correct = 0
for expected, text in TEST_CASES:
    t0 = time.perf_counter()
    scores = classify(text)
    best, conf = dominant(text)
    latency = (time.perf_counter() - t0) * 1000
    total += latency
    ok = best == expected
    correct += ok
    print(f"  {expected:15s} | detected={best:15s} | conf={conf:.2f} | {latency:.2f} ms | {'PASS' if ok else 'FAIL'}")

print("=" * 50)
print(f"Accuracy: {correct}/{len(TEST_CASES)} ({correct*100//len(TEST_CASES)}%)")
print(f"Avg latency: {total/len(TEST_CASES):.2f} ms")
