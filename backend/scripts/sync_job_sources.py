"""Run one bounded sync across every enabled public ATS board."""

from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.models  # noqa: E402, F401
from app.core.database import SessionLocal  # noqa: E402
from app.services.job_connectors import (  # noqa: E402
    ConnectorError,
    configured_connectors,
    sync_connector,
)


def main() -> int:
    connectors = configured_connectors()
    if not connectors:
        print("No public ATS connectors are enabled and configured.")
        return 0

    failures = 0
    with SessionLocal() as db:
        for connector in connectors:
            connector_name = f"{connector.source_name}/{connector.source_scope}"
            try:
                result = sync_connector(db, connector)
            except ConnectorError as exc:
                db.rollback()
                failures += 1
                print(f"{connector_name}: failed: {exc}", file=sys.stderr)
                continue
            print(
                f"{connector_name}: "
                f"seen={result['seen']} created={result['created']} "
                f"removed={result['removed']}"
            )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
