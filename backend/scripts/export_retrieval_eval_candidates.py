from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.models.application import Application
from app.models.project_evidence_chunk import ProjectEvidenceChunk
from app.models.user import User
from app.services.retrieval_service import build_application_query_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export RolePilot retrieval corpus and real application queries for manual labeling."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evals/retrieval_eval.local.json"),
        help="Destination JSON file.",
    )
    parser.add_argument(
        "--owner-subject",
        required=True,
        help="Exact OIDC subject whose private rows should be exported.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = SessionLocal()

    try:
        db.execute(
            text("SELECT set_config('app.current_subject', :subject, true)"),
            {"subject": args.owner_subject},
        )
        owner = (
            db.query(User)
            .filter(User.external_subject == args.owner_subject)
            .first()
        )
        if owner is None:
            raise SystemExit("No user exists for --owner-subject.")
        db.execute(
            text("SELECT set_config('app.current_user_id', :user_id, true)"),
            {"user_id": str(owner.id)},
        )
        chunks = (
            db.query(ProjectEvidenceChunk)
            .filter(ProjectEvidenceChunk.user_id == owner.id)
            .order_by(ProjectEvidenceChunk.id)
            .all()
        )
        applications = (
            db.query(Application)
            .filter(Application.user_id == owner.id)
            .order_by(Application.id)
            .all()
        )

        payload = {
            "corpus": [
                {
                    "id": f"chunk-{chunk.id}",
                    "db_chunk_id": chunk.id,
                    "project_evidence_id": chunk.project_evidence_id,
                    "chunk_type": chunk.chunk_type,
                    "text": chunk.chunk_text,
                }
                for chunk in chunks
            ],
            "queries": [
                {
                    "id": f"application-{application.id}",
                    "source": "postgres",
                    "application_id": application.id,
                    "company": application.company,
                    "role_title": application.role_title,
                    "query_text": build_application_query_text(application),
                    "application": {
                        "company": application.company,
                        "role_title": application.role_title,
                        "ai_summary": application.ai_summary,
                        "required_skills": application.required_skills or [],
                        "preferred_skills": application.preferred_skills or [],
                        "keywords": application.keywords or [],
                        "job_description": application.job_description or "",
                    },
                    "relevance": {},
                    "labeling_notes": "Fill relevance with {chunk-id: 0|1|2} after manual review.",
                }
                for application in applications
            ],
        }

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w") as handle:
            json.dump(payload, handle, indent=2)

        print(
            f"Exported {len(payload['corpus'])} chunks and {len(payload['queries'])} queries "
            f"to {args.output}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
