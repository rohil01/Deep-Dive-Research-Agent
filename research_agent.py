"""Backward-compatible entry point.

The agent now lives in the ``finsight`` package (see ``src/finsight/``).
This shim keeps ``python research_agent.py "query"`` working.

Preferred usage after ``pip install -e .``:

    finsight research "Your research question" -o report.md
"""
import sys
from pathlib import Path

# Allow running from a source checkout without installation
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finsight.cli import app  # noqa: E402

if __name__ == "__main__":
    # Default to the `research` command for convenience:
    #   python research_agent.py "your query"
    if len(sys.argv) > 1 and sys.argv[1] not in ("research", "--help"):
        sys.argv.insert(1, "research")
    app()
