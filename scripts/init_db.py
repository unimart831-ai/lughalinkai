"""Initialize LughaLink database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.database import init_database

if __name__ == "__main__":
    init_database()
    print("LughaLink database ready.")
