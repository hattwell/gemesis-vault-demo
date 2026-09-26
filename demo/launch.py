"""Seed a fresh ephemeral fixture before importing any DB-dependent runtime code."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from demo.seed import build_demo_database


def main() -> None:
    import uvicorn

    with tempfile.TemporaryDirectory(prefix="gemesis-fictional-demo-") as temporary:
        path = Path(temporary) / "gemesis.db"
        build_demo_database(path)
        previous = os.environ.get("DEMO_DB_PATH")
        os.environ["DEMO_DB_PATH"] = str(path)
        try:
            from demo.app import app  # no DB-dependent import before the seeded path exists

            uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")),
                        access_log=False, log_level="warning")
        finally:
            if previous is None:
                os.environ.pop("DEMO_DB_PATH", None)
            else:
                os.environ["DEMO_DB_PATH"] = previous


if __name__ == "__main__":
    main()
