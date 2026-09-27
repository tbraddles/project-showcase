from pathlib import Path
import sys

SPORT = Path(__file__).resolve().parents[1]
REPO = SPORT.parent
for path in (SPORT, REPO):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
