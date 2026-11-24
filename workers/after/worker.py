"""WP11-Worker über IPC v1."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from workers.after.adapter import AfterAdapter
from workers.rave.runtime import serve

if __name__ == "__main__":
    serve(AfterAdapter())
