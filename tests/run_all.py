"""
Runs every test module in tests/ that doesn't need a real embedding model,
GPU, or fine-tuned brain — everything here uses stubs/fakes and runs in a
couple of seconds. Use this before a demo to sanity-check nothing's broken.

Usage:  python tests/run_all.py
"""
import subprocess
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent

TEST_FILES = [
    "test_router.py",
    "test_retriever.py",
    "test_socratic_engine.py",
    "test_grounding.py",
    "test_visualization.py",
    "test_learning.py",
]


def main():
    failures = []
    for name in TEST_FILES:
        path = TEST_DIR / name
        print(f"\n=== {name} ===")
        result = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(PROJECT_ROOT),
            env={"PYTHONPATH": str(PROJECT_ROOT), **__import__("os").environ},
        )
        if result.returncode != 0:
            failures.append(name)

    print("\n" + "=" * 40)
    if failures:
        print(f"FAILED: {', '.join(failures)}")
        sys.exit(1)
    else:
        print("All test modules passed.")


if __name__ == "__main__":
    main()
