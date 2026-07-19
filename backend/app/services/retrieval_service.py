'''
This file gives you:

chunk_project_evidence()

turns one project into multiple chunks

embed_text()

calls OpenAI embeddings using text-embedding-3-small

rebuild_project_evidence_chunks_for_project()

deletes old chunks for a project and rebuilds them with embeddings

retrieve_relevant_chunks_for_application_keyword()

provides a deterministic keyword-overlap baseline for benchmarking
against semantic retrieval
'''
from collections import Counter
import hashlib
import re
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.models.project_evidence import ProjectEvidence
from app.models.application import Application
from app.models.project_evidence_chunk import ProjectEvidenceChunk

client = OpenAI(api_key=settings.openai_api_key)
EMBEDDING_MODEL = "text-embedding-3-small"

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9+#./-]*")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "into", "is", "it", "of", "on", "or", "that", "the", "to",
    "with", "you", "your",
}


def chunk_project_evidence(project: ProjectEvidence) -> list[dict]:
    chunks = []

    main_chunk_text = "\n".join(
        [
            f"Title: {project.title}",
            f"Category: {project.category}",
            f"Description: {project.description}",
            f"Skills: {', '.join(project.skills or [])}",
            f"Keywords: {', '.join(project.keywords or [])}",
            f"Outcome: {project.outcome or ''}",
            f"Dates: {' to '.join(part for part in [project.start_date, project.end_date] if part)}",
            f"Verified Metrics: {project.verified_metrics or []}",
            f"Links: {', '.join(project.links or [])}",
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
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def tokenize_for_keyword_search(text: str) -> list[str]:
    tokens = [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text or "")]
    return [token for token in tokens if token not in STOPWORDS]


def score_text_by_keyword_overlap(query_text: str, candidate_text: str) -> tuple[int, int, int]:
    query_tokens = tokenize_for_keyword_search(query_text)
    candidate_tokens = tokenize_for_keyword_search(candidate_text)

    if not query_tokens or not candidate_tokens:
        return (0, 0, 0)

    query_counter = Counter(query_tokens)
    candidate_counter = Counter(candidate_tokens)

    overlapping_tokens = set(query_counter).intersection(candidate_counter)
    unique_overlap = len(overlapping_tokens)
    total_overlap = sum(min(query_counter[token], candidate_counter[token]) for token in overlapping_tokens)
    rare_token_overlap = sum(
        1 for token in overlapping_tokens
        if len(token) > 3 and not token.isdigit()
    )

    return (unique_overlap, total_overlap, rare_token_overlap)


def rank_chunks_by_keyword_overlap(
    *,
    query_text: str,
    chunks: list[ProjectEvidenceChunk],
    top_k: int = 5,
) -> list[ProjectEvidenceChunk]:
    scored_chunks = []

    for chunk in chunks:
        score = score_text_by_keyword_overlap(query_text, chunk.chunk_text)
        if score[0] == 0:
            continue

        scored_chunks.append((score, chunk.id, chunk))

    scored_chunks.sort(key=lambda item: (-item[0][0], -item[0][1], -item[0][2], item[1]))
    return [chunk for _, _, chunk in scored_chunks[:top_k]]


def fuse_ranked_chunks_with_rrf(
    *,
    ranked_lists: list[list[ProjectEvidenceChunk]],
    top_k: int = 5,
    rrf_k: int = 60,
) -> list[ProjectEvidenceChunk]:
    fused_scores: dict[int, float] = {}
    chunk_by_id: dict[int, ProjectEvidenceChunk] = {}

    for ranked_chunks in ranked_lists:
        for rank, chunk in enumerate(ranked_chunks, start=1):
            chunk_by_id[chunk.id] = chunk
            fused_scores[chunk.id] = fused_scores.get(chunk.id, 0.0) + (1.0 / (rrf_k + rank))

    ordered_chunk_ids = sorted(
        fused_scores,
        key=lambda chunk_id: (-fused_scores[chunk_id], chunk_id),
    )
    return [chunk_by_id[chunk_id] for chunk_id in ordered_chunk_ids[:top_k]]


def rebuild_project_evidence_chunks_for_project(
    *,
    db: Session,
    project: ProjectEvidence,
) -> list[ProjectEvidenceChunk]:
    db.query(ProjectEvidenceChunk).filter(
        ProjectEvidenceChunk.project_evidence_id == project.id,
        ProjectEvidenceChunk.user_id == project.user_id,
    ).delete(synchronize_session=False)
    db.flush()

    chunks = chunk_project_evidence(project)
    saved_chunks = []

    for chunk in chunks:
        embedding = embed_text(chunk["chunk_text"])

        chunk_row = ProjectEvidenceChunk(
            user_id=project.user_id,
            project_evidence_id=project.id,
            chunk_text=chunk["chunk_text"],
            chunk_type=chunk["chunk_type"],
            source_version=project.version,
            section=project.category,
            title=project.title,
            dates=" to ".join(
                part for part in [project.start_date, project.end_date] if part
            ) or None,
            skills=project.skills or [],
            embedding_model=EMBEDDING_MODEL,
            content_hash=hashlib.sha256(
                chunk["chunk_text"].encode("utf-8")
            ).hexdigest(),
            embedding=embedding,
        )

        db.add(chunk_row)
        saved_chunks.append(chunk_row)

    db.flush()
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
        SELECT chunk.id
        FROM project_evidence_chunks AS chunk
        WHERE chunk.user_id = :user_id
          AND chunk.embedding IS NOT NULL
          AND EXISTS (
              SELECT 1
              FROM project_evidence AS evidence
              WHERE evidence.id = chunk.project_evidence_id
                AND evidence.user_id = chunk.user_id
                AND evidence.ingestion_status = 'ready'
          )
        ORDER BY chunk.embedding <=> :query_embedding
        LIMIT :top_k
        """
    )

    rows = db.execute(
        sql,
        {
            "query_embedding": str(query_embedding),
            "user_id": str(application.user_id),
            "top_k": top_k,
        },
    ).fetchall()

    chunk_ids = [row[0] for row in rows]

    if not chunk_ids:
        return []

    chunks = (
        db.query(ProjectEvidenceChunk)
        .join(
            ProjectEvidence,
            (ProjectEvidence.id == ProjectEvidenceChunk.project_evidence_id)
            & (ProjectEvidence.user_id == ProjectEvidenceChunk.user_id),
        )
        .filter(
            ProjectEvidenceChunk.id.in_(chunk_ids),
            ProjectEvidenceChunk.user_id == application.user_id,
            ProjectEvidence.ingestion_status == "ready",
        )
        .all()
    )

    chunk_map = {chunk.id: chunk for chunk in chunks}
    ordered_chunks = [chunk_map[chunk_id] for chunk_id in chunk_ids if chunk_id in chunk_map]

    return ordered_chunks


def retrieve_relevant_chunks_for_application_keyword(
    *,
    db: Session,
    application: Application,
    top_k: int = 5,
) -> list[ProjectEvidenceChunk]:
    query_text = build_application_query_text(application)
    chunks = (
        db.query(ProjectEvidenceChunk)
        .join(
            ProjectEvidence,
            (ProjectEvidence.id == ProjectEvidenceChunk.project_evidence_id)
            & (ProjectEvidence.user_id == ProjectEvidenceChunk.user_id),
        )
        .filter(
            ProjectEvidenceChunk.user_id == application.user_id,
            ProjectEvidence.ingestion_status == "ready",
        )
        .all()
    )
    return rank_chunks_by_keyword_overlap(
        query_text=query_text,
        chunks=chunks,
        top_k=top_k,
    )


def retrieve_relevant_chunks_for_application_hybrid(
    *,
    db: Session,
    application: Application,
    top_k: int = 5,
    semantic_candidate_k: int = 10,
    keyword_candidate_k: int = 10,
    rrf_k: int = 60,
) -> list[ProjectEvidenceChunk]:
    semantic_chunks = retrieve_relevant_chunks_for_application(
        db=db,
        application=application,
        top_k=max(top_k, semantic_candidate_k),
    )
    keyword_chunks = retrieve_relevant_chunks_for_application_keyword(
        db=db,
        application=application,
        top_k=max(top_k, keyword_candidate_k),
    )

    return fuse_ranked_chunks_with_rrf(
        ranked_lists=[semantic_chunks, keyword_chunks],
        top_k=top_k,
        rrf_k=rrf_k,
    )
