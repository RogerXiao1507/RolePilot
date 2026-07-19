from __future__ import annotations

import argparse
from pathlib import Path
import sys
from uuid import UUID

from sqlalchemy import select, update

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.models.application import Application
from app.models.application_full_resume_draft import ApplicationFullResumeDraft
from app.models.application_resume_match import ApplicationResumeMatch
from app.models.application_tailored_resume import ApplicationTailoredResume
from app.models.project_evidence import ProjectEvidence
from app.models.project_evidence_chunk import ProjectEvidenceChunk
from app.models.resume import Resume
from app.models.resume_source_item import ResumeSourceItem
from app.models.user import User


LEGACY_USER_ID = UUID("00000000-0000-4000-8000-000000000001")
OWNED_MODELS = (
    ApplicationResumeMatch,
    ApplicationTailoredResume,
    ApplicationFullResumeDraft,
    ProjectEvidenceChunk,
    ResumeSourceItem,
    Application,
    Resume,
    ProjectEvidence,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Explicitly transfer quarantined pre-authentication rows to a verified user."
    )
    parser.add_argument("--target-subject", required=True, help="Exact verified OIDC subject.")
    parser.add_argument(
        "--confirm-transfer-legacy-data",
        action="store_true",
        help="Required acknowledgement that all quarantined rows belong to this user.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.confirm_transfer_legacy_data:
        raise SystemExit("Refusing transfer without --confirm-transfer-legacy-data.")

    with SessionLocal() as db:
        target = db.scalar(
            select(User).where(User.external_subject == args.target_subject)
        )
        if target is None:
            raise SystemExit("Target user does not exist; the user must sign in first.")

        legacy = db.get(User, LEGACY_USER_ID)
        if legacy is None:
            print("No quarantined legacy principal remains; nothing to transfer.")
            return

        transferred: dict[str, int] = {}
        for model in OWNED_MODELS:
            result = db.execute(
                update(model)
                .where(model.user_id == LEGACY_USER_ID)
                .values(user_id=target.id)
            )
            transferred[model.__tablename__] = result.rowcount

        db.delete(legacy)
        db.commit()

    total = sum(transferred.values())
    print(f"Transferred {total} rows to {args.target_subject} and removed the legacy principal.")
    for table_name, count in transferred.items():
        print(f"  {table_name}: {count}")


if __name__ == "__main__":
    main()
