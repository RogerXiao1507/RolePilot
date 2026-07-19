from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import JobRecency, JobSort
from app.models.discovered_job import DiscoveredJob, JobSourcePosting
from app.models.job_discovery_action import JobDiscoveryAction
from app.models.job_search import JobSearch
from app.models.resume import Resume


RECENCY_DAYS = {
    JobRecency.DAY: 1,
    JobRecency.WEEK: 7,
    JobRecency.TWO_WEEKS: 14,
    JobRecency.MONTH: 30,
}
TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9+#.\-/]{1,}")
STOP_WORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "but",
    "for",
    "from",
    "have",
    "into",
    "our",
    "that",
    "the",
    "their",
    "this",
    "with",
    "will",
    "you",
    "your",
}


@dataclass(frozen=True)
class RankedJob:
    job: DiscoveredJob
    sources: list[JobSourcePosting]
    action_state: str | None
    preference_match_score: float
    resume_match_score: float | None
    recommended_score: float
    match_reasons: list[str]


def _normalize(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _tokens(value: str | None) -> set[str]:
    return {
        token
        for token in TOKEN_PATTERN.findall(_normalize(value))
        if token not in STOP_WORDS and len(token) > 2
    }


def _matches_any(value: str | None, preferences: list[str]) -> bool:
    normalized = _normalize(value)
    return any(_normalize(preference) in normalized for preference in preferences)


def passes_preference_filters(job: DiscoveredJob, search: JobSearch) -> bool:
    haystack = _normalize(f"{job.title} {job.company_name} {job.description}")
    if any(_normalize(company) in job.company_normalized for company in search.excluded_companies):
        return False
    if any(_normalize(keyword) in haystack for keyword in search.excluded_keywords):
        return False
    if search.required_keywords and not all(
        _normalize(keyword) in haystack for keyword in search.required_keywords
    ):
        return False
    if (
        search.employment_types
        and job.employment_type
        and job.employment_type not in {_normalize(value).replace(" ", "_") for value in search.employment_types}
    ):
        return False
    if (
        search.workplace_types
        and job.workplace_type
        and job.workplace_type not in {_normalize(value) for value in search.workplace_types}
    ):
        return False
    if (
        search.seniority_levels
        and job.seniority_level
        and job.seniority_level not in {_normalize(value) for value in search.seniority_levels}
    ):
        return False
    if search.locations and job.workplace_type != "remote" and not _matches_any(
        job.location, search.locations
    ):
        return False
    if search.salary_min is not None and job.salary_max is not None:
        if job.salary_max < search.salary_min:
            return False
    if search.salary_max is not None and job.salary_min is not None:
        if job.salary_min > search.salary_max:
            return False
    return True


def score_preference_match(job: DiscoveredJob, search: JobSearch) -> tuple[float, list[str]]:
    weighted: list[tuple[float, bool]] = []
    reasons: list[str] = []
    titles = search.target_titles + search.adjacent_titles
    title_match = _matches_any(job.title, titles)
    weighted.append((0.5, title_match))
    if title_match:
        reasons.append("Title matches a target or adjacent role")

    if search.required_keywords:
        haystack = _normalize(f"{job.title} {job.description}")
        keyword_count = sum(
            _normalize(keyword) in haystack for keyword in search.required_keywords
        )
        keyword_match = keyword_count / len(search.required_keywords)
        weighted.append((0.25, keyword_match))
        if keyword_count:
            reasons.append(
                f"Matches {keyword_count} of {len(search.required_keywords)} required keywords"
            )
    if search.locations:
        location_match = job.workplace_type == "remote" or _matches_any(
            job.location, search.locations
        )
        weighted.append((0.1, location_match))
        if location_match:
            reasons.append("Location or remote preference matches")
    if search.workplace_types and job.workplace_type:
        workplace_match = job.workplace_type in {
            _normalize(value) for value in search.workplace_types
        }
        weighted.append((0.05, workplace_match))
        if workplace_match:
            reasons.append(f"Workplace type is {job.workplace_type}")
    if search.employment_types and job.employment_type:
        employment_match = job.employment_type in {
            _normalize(value).replace(" ", "_") for value in search.employment_types
        }
        weighted.append((0.05, employment_match))
        if employment_match:
            reasons.append("Employment type matches")
    if search.seniority_levels and job.seniority_level:
        seniority_match = job.seniority_level in {
            _normalize(value) for value in search.seniority_levels
        }
        weighted.append((0.05, seniority_match))
        if seniority_match:
            reasons.append("Experience level matches")

    total_weight = sum(weight for weight, _ in weighted)
    score = sum(weight * float(match) for weight, match in weighted) / total_weight
    return round(score, 4), reasons[:4]


def score_resume_match(job: DiscoveredJob, resume: Resume | None) -> float | None:
    if resume is None:
        return None
    job_tokens = _tokens(f"{job.title} {job.description}")
    if not job_tokens:
        return 0.0
    resume_tokens = _tokens(f"{resume.summary} {resume.extracted_text}")
    overlap = len(job_tokens & resume_tokens)
    # A saturating score avoids long descriptions suppressing real skill overlap.
    return round(min(1.0, overlap / 12), 4)


def freshness_label(posted_at: datetime | None, *, now: datetime | None = None) -> str:
    if posted_at is None:
        return "Date unavailable"
    current = now or datetime.now(timezone.utc)
    age_days = max(0, (current - posted_at).days)
    if age_days == 0:
        return "Posted today"
    if age_days == 1:
        return "Posted 1 day ago"
    return f"Posted {age_days} days ago"


def _freshness_score(posted_at: datetime | None, now: datetime) -> float:
    if posted_at is None:
        return 0.0
    age_days = max(0.0, (now - posted_at).total_seconds() / 86_400)
    return math.exp(-age_days / 14)


def build_discovery_feed(
    db: Session,
    *,
    search: JobSearch,
    user_id,
    recency: JobRecency,
    sort: JobSort,
    limit: int,
    now: datetime | None = None,
) -> list[RankedJob]:
    current = now or datetime.now(timezone.utc)
    stmt = select(DiscoveredJob).where(
        DiscoveredJob.verification_status == "active"
    )
    if recency != JobRecency.ALL:
        cutoff = current - timedelta(days=RECENCY_DAYS[recency])
        stmt = stmt.where(
            DiscoveredJob.source_posted_at.is_not(None),
            DiscoveredJob.source_posted_at >= cutoff,
        )
    jobs = db.scalars(stmt.limit(1000)).all()
    job_ids = [job.id for job in jobs]
    sources_by_job: dict = {job_id: [] for job_id in job_ids}
    actions_by_job: dict = {}
    if job_ids:
        for source in db.scalars(
            select(JobSourcePosting).where(
                JobSourcePosting.discovered_job_id.in_(job_ids),
                JobSourcePosting.verification_status == "active",
            )
        ).all():
            sources_by_job[source.discovered_job_id].append(source)
        actions_by_job = {
            action.discovered_job_id: action
            for action in db.scalars(
                select(JobDiscoveryAction).where(
                    JobDiscoveryAction.user_id == user_id,
                    JobDiscoveryAction.discovered_job_id.in_(job_ids),
                )
            ).all()
        }

    resume = None
    if search.resume_id:
        resume = db.scalar(
            select(Resume).where(
                Resume.id == search.resume_id,
                Resume.user_id == user_id,
                Resume.is_archived.is_(False),
            )
        )

    ranked: list[RankedJob] = []
    for job in jobs:
        action = actions_by_job.get(job.id)
        if action and action.state in {"dismissed", "duplicate", "converted"}:
            continue
        if not passes_preference_filters(job, search):
            continue
        preference_score, reasons = score_preference_match(job, search)
        resume_score = score_resume_match(job, resume)
        relevance_score = (
            preference_score
            if resume_score is None
            else (preference_score * 0.75) + (resume_score * 0.25)
        )
        recommended_score = (relevance_score * 0.8) + (
            _freshness_score(job.source_posted_at, current) * 0.2
        )
        ranked.append(
            RankedJob(
                job=job,
                sources=sources_by_job.get(job.id, []),
                action_state=action.state if action else None,
                preference_match_score=preference_score,
                resume_match_score=resume_score,
                recommended_score=round(recommended_score, 4),
                match_reasons=reasons or ["Matches the saved search filters"],
            )
        )

    if sort == JobSort.NEWEST:
        ranked.sort(
            key=lambda item: (
                item.job.source_posted_at is not None,
                item.job.source_posted_at or datetime.min.replace(tzinfo=timezone.utc),
                item.preference_match_score,
            ),
            reverse=True,
        )
    elif sort == JobSort.MOST_RELEVANT:
        ranked.sort(
            key=lambda item: (
                item.preference_match_score
                if item.resume_match_score is None
                else item.preference_match_score * 0.75 + item.resume_match_score * 0.25,
                item.job.source_posted_at or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )
    else:
        ranked.sort(
            key=lambda item: (
                item.recommended_score,
                item.job.source_posted_at or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )
    return ranked[:limit]
