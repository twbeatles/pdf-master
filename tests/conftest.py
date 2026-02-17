import sys
from pathlib import Path


# pytest 9 can run with importlib import mode where cwd isn't reliably on sys.path.
# Ensure the repo root (which contains the `src/` package) is importable.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

