from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.models.project_evidence import ProjectEvidence
from app.models.project_evidence_chunk import ProjectEvidenceChunk
from app.services.retrieval_service import rebuild_project_evidence_chunks_for_project


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed project evidence rows from a local JSON file and rebuild chunk embeddings."
    )
    parser.add_argument(
        "--seed-file",
        type=Path,
        default=Path("seeds/project_evidence.roger.json"),
        help="Path to the seed JSON file.",
    )
    parser.add_argument(
        "--drop-placeholder",
        action="store_true",
        help="Delete obvious placeholder evidence rows like title='string'.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with args.seed_file.open() as handle:
        entries = json.load(handle)

    db = SessionLocal()
    try:
        if args.drop_placeholder:
            placeholders = (
                db.query(ProjectEvidence)
                .filter(ProjectEvidence.title.in_(["string", "test", "placeholder"]))
                .all()
            )
            for project in placeholders:
                db.query(ProjectEvidenceChunk).filter(
                    ProjectEvidenceChunk.project_evidence_id == project.id
                ).delete()
                db.delete(project)
            db.commit()

        for entry in entries:
            project = (
                db.query(ProjectEvidence)
                .filter(ProjectEvidence.title == entry["title"])
                .first()
            )

            if project is None:
                project = ProjectEvidence(
                    title=entry["title"],
                    category=entry["category"],
                    description=entry["description"],
                    skills=entry["skills"],
                    keywords=entry["keywords"],
                    bullet_bank=entry["bullet_bank"],
                )
                db.add(project)
                db.commit()
                db.refresh(project)
            else:
                project.category = entry["category"]
                project.description = entry["description"]
                project.skills = entry["skills"]
                project.keywords = entry["keywords"]
                project.bullet_bank = entry["bullet_bank"]
                db.commit()
                db.refresh(project)

            rebuild_project_evidence_chunks_for_project(db=db, project=project)
            print(f"Seeded and rebuilt chunks for: {project.title}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
