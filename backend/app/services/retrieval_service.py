'''
This file gives you:

chunk_project_evidence()

turns one project into multiple chunks

embed_text()

calls OpenAI embeddings using text-embedding-3-small

rebuild_project_evidence_chunks_for_project()

deletes old chunks for a project and rebuilds them with embeddings

'''
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.models.project_evidence import ProjectEvidence
from app.models.application import Application
from app.models.project_evidence_chunk import ProjectEvidenceChunk

client = OpenAI(api_key=settings.openai_api_key)


def chunk_project_evidence(project: ProjectEvidence) -> list[dict]:
    chunks = []

    main_chunk_text = "\n".join(
        [
            f"Title: {project.title}",
            f"Category: {project.category}",
            f"Description: {project.description}",
            f"Skills: {', '.join(project.skills or [])}",
            f"Keywords: {', '.join(project.keywords or [])}",
        ]
    )
    chunks.append(
        {
            "chunk_type": "summary",
            "chunk_text": main_chunk_text,
        }
    )

    for bullet in project.bullet_bank or []:
        bullet_text = "\n".join(
            [
                f"Title: {project.title}",
                f"Category: {project.category}",
                f"Bullet: {bullet}",
            ]
        )
        chunks.append(
            {
                "chunk_type": "bullet",
                "chunk_text": bullet_text,
            }
        )

    return chunks


def embed_text(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


def rebuild_project_evidence_chunks_for_project(
    *,
    db: Session,
    project: ProjectEvidence,
) -> list[ProjectEvidenceChunk]:
    db.query(ProjectEvidenceChunk).filter(
        ProjectEvidenceChunk.project_evidence_id == project.id
    ).delete()

    chunks = chunk_project_evidence(project)
    saved_chunks = []

    for chunk in chunks:
        embedding = embed_text(chunk["chunk_text"])

        chunk_row = ProjectEvidenceChunk(
            project_evidence_id=project.id,
            chunk_text=chunk["chunk_text"],
            chunk_type=chunk["chunk_type"],
            embedding=embedding,
        )

        db.add(chunk_row)
        saved_chunks.append(chunk_row)

    db.commit()

    for chunk_row in saved_chunks:
        db.refresh(chunk_row)

    return saved_chunks

def build_application_query_text(application: Application) -> str:
    parts = [
        f"Role Title: {application.role_title or ''}",
        f"Company: {application.company or ''}",
        f"AI Summary: {application.ai_summary or ''}",
        f"Required Skills: {', '.join(application.required_skills or [])}",
        f"Preferred Skills: {', '.join(application.preferred_skills or [])}",
        f"Keywords: {', '.join(application.keywords or [])}",
        f"Job Description: {application.job_description or ''}",
    ]
    return "\n".join(parts)


def retrieve_relevant_chunks_for_application(
    *,
    db: Session,
    application: Application,
    top_k: int = 5,
) -> list[ProjectEvidenceChunk]:
    query_text = build_application_query_text(application)
    query_embedding = embed_text(query_text)

    sql = text(
        """
        SELECT id
        FROM project_evidence_chunks
        ORDER BY embedding <=> :query_embedding
        LIMIT :top_k
        """
    )

    rows = db.execute(
        sql,
        {
            "query_embedding": str(query_embedding),
            "top_k": top_k,
        },
    ).fetchall()

    chunk_ids = [row[0] for row in rows]

    if not chunk_ids:
        return []

    chunks = (
        db.query(ProjectEvidenceChunk)
        .filter(ProjectEvidenceChunk.id.in_(chunk_ids))
        .all()
    )

    chunk_map = {chunk.id: chunk for chunk in chunks}
    ordered_chunks = [chunk_map[chunk_id] for chunk_id in chunk_ids if chunk_id in chunk_map]

    return ordered_chunks