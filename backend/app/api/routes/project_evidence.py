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

from app.api.deps import get_current_user, get_db
from app.models.project_evidence import ProjectEvidence
from app.models.user import User
from app.schemas.project_evidence import (
    ProjectEvidenceCreate,
    ProjectEvidenceResponse,
)
from app.services.retrieval_service import rebuild_project_evidence_chunks_for_project

router = APIRouter(prefix="/project-evidence", tags=["project-evidence"])


@router.post("", response_model=ProjectEvidenceResponse)
def create_project_evidence(
    payload: ProjectEvidenceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = ProjectEvidence(
        user_id=current_user.id,
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
def list_project_evidence(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    projects = (
        db.query(ProjectEvidence)
        .filter(ProjectEvidence.user_id == current_user.id)
        .order_by(ProjectEvidence.created_at.desc())
        .all()
    )
    return projects
