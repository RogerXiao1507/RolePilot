"""Operator-triggered bounded sync for configured public Greenhouse boards."""

from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.models  # noqa: E402, F401
from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.services.job_connectors import GreenhouseConnector, sync_connector  # noqa: E402


def main() -> int:
    if not settings.job_discovery_greenhouse_enabled:
        print("Greenhouse discovery is disabled by JOB_DISCOVERY_GREENHOUSE_ENABLED.")
        return 0
    if not settings.job_discovery_greenhouse_boards:
        print("No Greenhouse boards are configured.")
        return 0

    with SessionLocal() as db:
        for board_token in settings.job_discovery_greenhouse_boards:
            result = sync_connector(db, GreenhouseConnector(board_token))
            print(
                f"greenhouse/{board_token}: "
                f"seen={result['seen']} created={result['created']} removed={result['removed']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
