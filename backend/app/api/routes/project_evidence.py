'''
Now when you call POST /project-evidence:

it saves the project evidence row
it automatically chunks it
it generates embeddings
it stores those chunks in project_evidence_chunks

So the evidence becomes retrievable right away.
'''

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project_evidence import ProjectEvidence
from app.schemas.project_evidence import (
    ProjectEvidenceCreate,
    ProjectEvidenceResponse,
)
from app.services.retrieval_service import rebuild_project_evidence_chunks_for_project

router = APIRouter(prefix="/project-evidence", tags=["project-evidence"])


@router.post("", response_model=ProjectEvidenceResponse)
def create_project_evidence(
    payload: ProjectEvidenceCreate,
    db: Session = Depends(get_db),
):
    project = ProjectEvidence(
        title=payload.title,
        category=payload.category,
        description=payload.description,
        skills=payload.skills,
        keywords=payload.keywords,
        bullet_bank=payload.bullet_bank,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    rebuild_project_evidence_chunks_for_project(
        db=db,
        project=project,
    )

    return project


@router.get("", response_model=list[ProjectEvidenceResponse])
def list_project_evidence(db: Session = Depends(get_db)):
    projects = (
        db.query(ProjectEvidence)
        .order_by(ProjectEvidence.created_at.desc())
        .all()
    )
    return projects