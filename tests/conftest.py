"""Add src/code_context/ to sys.path for all tests."""
import sys
from pathlib import Path

SRC = str(Path(__file__).resolve().parent.parent / "src" / "code_context")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
