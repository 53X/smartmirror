"""Ensure service root and shared package are importable in tests."""

import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
SHARED_ROOT = SERVICE_ROOT.parents[1] / "shared"
for path in (SERVICE_ROOT, SHARED_ROOT):
    as_str = str(path)
    if as_str not in sys.path:
        sys.path.insert(0, as_str)
