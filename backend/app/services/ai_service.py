import json
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from openai import OpenAI

from app.core.config import settings
from app.models.application import Application
from app.models.project_evidence import ProjectEvidence
from app.models.resume import Resume
from app.models.resume_source_item import ResumeSourceItem
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.services.retrieval_service import retrieve_relevant_chunks_for_application_hybrid
from app.models.project_evidence_chunk import ProjectEvidenceChunk
from app.models.application_tailored_resume import ApplicationTailoredResume

client = OpenAI(api_key=settings.openai_api_key)

ALLOWED_JOB_CONTENT_TYPES = {
    "application/xhtml+xml",
    "text/html",
    "text/plain",
}
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}


class JobUrlValidationError(ValueError):
    """The supplied URL is not safe to request."""


class JobUrlFetchError(RuntimeError):
    """The remote job page could not be fetched safely."""


class GeneratedContentGroundingError(RuntimeError):
    """Generated content failed a deterministic grounding check."""


NUMBER_PATTERN = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*%?(?![A-Za-z0-9])")


def parse_job_description(text: str) -> dict:
    response = client.responses.create(
        model="gpt-5.4-mini",
        input=[
            {
                "role": "developer",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You extract structured information from internship and job postings. "
                            "Return only valid JSON that matches the provided schema. "
                            "Do not invent details. If a field is missing, return null or an empty list."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Parse this job description into structured data:\n\n{text}",
                    }
                ],
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "job_parser",
                "schema": {
                    "type": "object",
                    "properties": {
                        "company": {"type": ["string", "null"]},
                        "role_title": {"type": ["string", "null"]},
                        "location": {"type": ["string", "null"]},
                        "employment_type": {"type": ["string", "null"]},
                        "internship_season": {"type": ["string", "null"]},
                        "required_skills": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "preferred_skills": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "summary": {"type": "string"},
                        "next_steps": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "company",
                        "role_title",
                        "location",
                        "employment_type",
                        "internship_season",
                        "required_skills",
                        "preferred_skills",
                        "keywords",
                        "summary",
                        "next_steps",
                    ],
                    "additionalProperties": False,
                },
            }
        },
    )

    return json.loads(response.output_text)


def _resolve_public_addresses(hostname: str, port: int) -> set[str]:
    try:
        direct_address = ipaddress.ip_address(hostname)
        addresses = {str(direct_address)}
    except ValueError:
        try:
            address_info = socket.getaddrinfo(
                hostname,
                port,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise JobUrlValidationError("Job URL host could not be resolved.") from exc
        addresses = {item[4][0].split("%", 1)[0] for item in address_info}

    if not addresses:
        raise JobUrlValidationError("Job URL host could not be resolved.")

    for address in addresses:
        try:
            parsed_address = ipaddress.ip_address(address)
        except ValueError as exc:
            raise JobUrlValidationError("Job URL resolved to an invalid address.") from exc
        if not parsed_address.is_global:
            raise JobUrlValidationError(
                "Job URLs cannot resolve to private or local network addresses."
            )

    return addresses


def validate_public_job_url(url: str) -> str:
    try:
        parsed = urlsplit(url.strip())
        port = parsed.port
    except ValueError as exc:
        raise JobUrlValidationError("Job URL is invalid.") from exc

    if parsed.scheme not in {"http", "https"}:
        raise JobUrlValidationError("Job URL must use HTTP or HTTPS.")
    if not parsed.hostname:
        raise JobUrlValidationError("Job URL must include a hostname.")
    if parsed.username or parsed.password:
        raise JobUrlValidationError("Job URL cannot include embedded credentials.")

    expected_port = 443 if parsed.scheme == "https" else 80
    if port not in {None, expected_port}:
        raise JobUrlValidationError("Job URL must use the standard HTTP or HTTPS port.")

    _resolve_public_addresses(parsed.hostname, port or expected_port)
    return parsed.geturl()


def _read_limited_response(response: httpx.Response) -> bytes:
    content_length = response.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.job_url_max_response_bytes:
                raise JobUrlFetchError("Job posting response is too large.")
        except ValueError:
            pass

    payload = bytearray()
    for chunk in response.iter_bytes():
        payload.extend(chunk)
        if len(payload) > settings.job_url_max_response_bytes:
            raise JobUrlFetchError("Job posting response is too large.")
    return bytes(payload)


def extract_text_from_url(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
    }

    current_url = url.strip()
    timeout = httpx.Timeout(settings.job_url_timeout_seconds)

    try:
        with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as http_client:
            for redirect_count in range(settings.job_url_max_redirects + 1):
                current_url = validate_public_job_url(current_url)

                with http_client.stream("GET", current_url, headers=headers) as response:
                    if response.status_code in REDIRECT_STATUS_CODES:
                        location = response.headers.get("location")
                        if not location:
                            raise JobUrlFetchError("Job posting returned an invalid redirect.")
                        if redirect_count >= settings.job_url_max_redirects:
                            raise JobUrlFetchError("Job posting exceeded the redirect limit.")
                        current_url = urljoin(current_url, location)
                        continue

                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "")
                    media_type = content_type.split(";", 1)[0].strip().lower()
                    if media_type not in ALLOWED_JOB_CONTENT_TYPES:
                        raise JobUrlFetchError("Job URL did not return a supported text page.")

                    content = _read_limited_response(response)
                    encoding = response.encoding or "utf-8"
                    response_text = content.decode(encoding, errors="replace")
                    break
            else:
                raise JobUrlFetchError("Job posting exceeded the redirect limit.")
    except JobUrlValidationError:
        raise
    except JobUrlFetchError:
        raise
    except httpx.HTTPError as exc:
        raise JobUrlFetchError("Job posting could not be fetched.") from exc

    soup = BeautifulSoup(response_text, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = " ".join(text.split())

    return text


def parse_job_from_url(url: str) -> dict:
    extracted_text = extract_text_from_url(url)

    if not extracted_text or len(extracted_text) < 200:
        raise ValueError("Could not extract enough job description text from this URL.")

    return parse_job_description(extracted_text)


def match_resume_to_job(
    *,
    resume_text: str,
    role_title: str | None = None,
    company: str | None = None,
    job_summary: str | None = None,
    required_skills: list[str] | None = None,
    preferred_skills: list[str] | None = None,
    keywords: list[str] | None = None,
):
    required_skills = required_skills or []
    preferred_skills = preferred_skills or []
    keywords = keywords or []

    prompt = f"""
You are an expert career assistant.

Compare the candidate's resume against the job information and return a JSON object only.

Evaluate:
1. overall fit for the role
2. which skills/keywords from the job are clearly present in the resume
3. which important skills/keywords appear missing or weak
4. what strengths in the resume align well with the role
5. what improvement areas exist for this specific role
6. concrete resume changes that would make the candidate stronger for this job

Return JSON with exactly these keys:
overall_match_summary
matched_skills
missing_skills
strengths_for_role
improvement_areas
suggested_resume_changes

Rules:
- matched_skills and missing_skills should focus mainly on required_skills, preferred_skills, and keywords
- be specific and practical
- do not invent experience that is not in the resume
- keep suggested_resume_changes actionable
- each list should contain concise bullet-like strings
- overall_match_summary should be 3 to 5 sentences

Job info:
Role Title: {role_title or ""}
Company: {company or ""}
Job Summary: {job_summary or ""}
Required Skills: {required_skills}
Preferred Skills: {preferred_skills}
Keywords: {keywords}

Resume Text:
{resume_text}
"""

    response = client.responses.create(
        model="gpt-5.4-mini",
        input=prompt,
    )

    return json.loads(response.output_text)


def _tokenize_for_match(text: str) -> set[str]:
    return {
        token.strip(".,:;()[]{}!?\"'").lower()
        for token in text.split()
        if token.strip(".,:;()[]{}!?\"'")
    }


def _retrieve_relevant_project_evidence(
    *,
    application: Application,
    projects: list[ProjectEvidence],
    top_k: int = 3,
) -> list[ProjectEvidence]:
    query_parts = [
        application.role_title or "",
        application.ai_summary or "",
        " ".join(application.required_skills or []),
        " ".join(application.preferred_skills or []),
        " ".join(application.keywords or []),
        application.job_description or "",
    ]
    query_text = " ".join(query_parts)
    query_tokens = _tokenize_for_match(query_text)

    scored_projects = []

    for project in projects:
        project_text = " ".join(
            [
                project.title or "",
                project.category or "",
                project.description or "",
                " ".join(project.skills or []),
                " ".join(project.keywords or []),
                " ".join(project.bullet_bank or []),
            ]
        )
        project_tokens = _tokenize_for_match(project_text)

        overlap = len(query_tokens.intersection(project_tokens))
        scored_projects.append((overlap, project))

    scored_projects.sort(key=lambda item: item[0], reverse=True)

    relevant_projects = [project for score, project in scored_projects if score > 0]

    return relevant_projects[:top_k]


def tailor_resume_for_application(
    *,
    db: Session,
    application: Application,
    resume: Resume,
):
    relevant_chunks = retrieve_relevant_chunks_for_application_hybrid(
        db=db,
        application=application,
        top_k=5,
    )

    resume_source_items = []
    if getattr(resume, "id", None) is not None and hasattr(db, "scalars"):
        resume_source_items = list(
            db.scalars(
                select(ResumeSourceItem).where(
                    ResumeSourceItem.resume_id == resume.id,
                    ResumeSourceItem.user_id == resume.user_id,
                    ResumeSourceItem.is_active.is_(True),
                    ResumeSourceItem.source_version == resume.version,
                )
            ).all()
        )

    source_catalog: dict[tuple[str, str, int], str] = {}
    for item in resume_source_items:
        source_catalog[("resume_item", str(item.id), item.source_version)] = item.content
    for chunk in relevant_chunks:
        source_catalog[
            ("evidence", str(chunk.project_evidence_id), chunk.source_version)
        ] = chunk.chunk_text

    source_catalog_text = "\n\n".join(
        f"[{source_type} id={source_id} version={source_version}]\n{content}"
        for (source_type, source_id, source_version), content in source_catalog.items()
    )

    retrieved_evidence_text = "\n\n".join(
        [
            f"""
Chunk Type: {chunk.chunk_type}
Chunk Text:
{chunk.chunk_text}
""".strip()
            for chunk in relevant_chunks
        ]
    )

    prompt = f"""
You are an expert resume tailoring assistant.

Your job is to tailor resume content for a specific job using ONLY the user’s saved resume and the retrieved project evidence below.

Do not invent experience.
Do not add tools, metrics, or accomplishments unless they are supported by the provided evidence.
Prefer strong, concise, recruiter-friendly language.

Return JSON only with exactly these keys:
tailored_summary
tailored_skills
tailored_bullets
tailoring_notes

Rules:
- tailored_summary must be a single string of 3 to 5 sentences
- tailored_skills must be a list of concise skills relevant to the target role
- tailored_skills may include ATS-relevant skills that are reasonably supported by the provided evidence, even if the exact wording is not already on the resume
- do not include far-fetched, unsupported, or invented skills
- tailored_bullets must be a list of objects with exactly these keys:
  - section
  - source_title
  - original_bullet
  - tailored_bullet
  - evidence_used
  - citations
- section should be something like "Projects", "Research", "Experience", or "Skills"
- source_title should identify the project, role, or source area the bullet comes from
- original_bullet should identify the resume or project bullet that should be replaced
- tailored_bullet should be the improved replacement bullet
- evidence_used should be a short list naming the specific source evidence used, such as project titles or "Saved Resume"
- citations must be a list with at least one exact source from the Source Catalog. Each citation object must contain source_type, source_id, and source_version. Never invent an ID or version.
- tailored_bullet should aim to follow XYZ style:
  Accomplished X as measured by Y by doing Z
- prefer quantified results when supported by the provided evidence
- if an exact metric is not supported, use a concrete non-fabricated outcome instead of inventing numbers
- tailoring_notes must be a list of concise strings explaining what was emphasized, what ATS-relevant skills were surfaced, and what gaps remain, and no need to mention willingness to work onsite or U.S status
- Use the job's required skills, preferred skills, and keywords to guide the tailoring
- Stay grounded in the provided evidence only

Job Information:
Company: {application.company}
Role Title: {application.role_title}
Job Summary: {application.ai_summary or ""}
Required Skills: {application.required_skills or []}
Preferred Skills: {application.preferred_skills or []}
Keywords: {application.keywords or []}
Job Description: {application.job_description or ""}

Saved Resume:
File Name: {resume.file_name}
Summary: {resume.summary}
Strengths: {resume.strengths}
Weaknesses: {resume.weaknesses}
Wording Issues: {resume.wording_issues}
Missing Metrics: {resume.missing_metrics}
Suggested Improvements: {resume.suggested_improvements}
Extracted Resume Text:
{resume.extracted_text}

Retrieved Project Evidence:
{retrieved_evidence_text if retrieved_evidence_text else "No additional project evidence retrieved."}

Source Catalog for citations:
{source_catalog_text if source_catalog_text else "No structured source catalog is available."}
"""

    response = client.responses.create(
        model="gpt-5.4-mini",
        input=prompt,
    )

    result = json.loads(response.output_text)

    if isinstance(result.get("tailored_summary"), list):
        result["tailored_summary"] = " ".join(
            str(item).strip() for item in result["tailored_summary"] if str(item).strip()
        )

    if result.get("tailored_summary") is None:
        result["tailored_summary"] = ""

    if not isinstance(result.get("tailored_summary"), str):
        result["tailored_summary"] = str(result["tailored_summary"])

    if isinstance(result.get("tailored_skills"), str):
        result["tailored_skills"] = [result["tailored_skills"]]

    if "tailored_skills" not in result or result["tailored_skills"] is None:
        result["tailored_skills"] = []

    normalized_skills = []
    for skill in result["tailored_skills"]:
        if skill is None:
            continue
        normalized_skills.append(str(skill).strip())

    grounding_source_text = "\n\n".join(
        part for part in [resume.extracted_text, retrieved_evidence_text] if part
    )

    def source_contains_term(term: str) -> bool:
        cleaned = " ".join(term.strip().split())
        if not cleaned:
            return False
        return re.search(
            rf"(?<![A-Za-z0-9]){re.escape(cleaned)}(?![A-Za-z0-9])",
            grounding_source_text,
            re.IGNORECASE,
        ) is not None

    result["tailored_skills"] = [
        skill for skill in normalized_skills if skill and source_contains_term(skill)
    ]

    if isinstance(result.get("tailoring_notes"), str):
        result["tailoring_notes"] = [result["tailoring_notes"]]

    if "tailoring_notes" not in result or result["tailoring_notes"] is None:
        result["tailoring_notes"] = []

    normalized_notes = []
    for note in result["tailoring_notes"]:
        if note is None:
            continue
        normalized_notes.append(str(note).strip())

    result["tailoring_notes"] = [note for note in normalized_notes if note]

    if "tailored_bullets" not in result or result["tailored_bullets"] is None:
        result["tailored_bullets"] = []

    normalized_bullets = []
    for bullet in result["tailored_bullets"]:
        if not isinstance(bullet, dict):
            continue

        evidence_used = bullet.get("evidence_used", [])
        if isinstance(evidence_used, str):
            evidence_used = [evidence_used]
        if evidence_used is None:
            evidence_used = []

        normalized_evidence = []
        for item in evidence_used:
            if item is None:
                continue
            normalized_evidence.append(str(item).strip())

        normalized_citations = []
        for citation in bullet.get("citations") or []:
            if not isinstance(citation, dict):
                continue
            try:
                source_version = int(citation.get("source_version"))
            except (TypeError, ValueError):
                continue
            key = (
                str(citation.get("source_type") or "").strip(),
                str(citation.get("source_id") or "").strip(),
                source_version,
            )
            if key not in source_catalog:
                continue
            normalized_citations.append(
                {
                    "source_type": key[0],
                    "source_id": key[1],
                    "source_version": key[2],
                }
            )

        if source_catalog and not normalized_citations:
            comparison_text = " ".join(
                str(bullet.get(field) or "")
                for field in ("source_title", "original_bullet", "tailored_bullet")
            )
            comparison_tokens = _tokenize_for_match(comparison_text)
            ranked_sources = sorted(
                source_catalog.items(),
                key=lambda item: len(
                    comparison_tokens.intersection(_tokenize_for_match(item[1]))
                ),
                reverse=True,
            )
            if ranked_sources:
                key, _content = ranked_sources[0]
                normalized_citations = [
                    {
                        "source_type": key[0],
                        "source_id": key[1],
                        "source_version": key[2],
                    }
                ]

        normalized_bullets.append(
            {
                "section": str(bullet.get("section", "Projects")).strip(),
                "source_title": str(bullet.get("source_title", "Saved Resume")).strip(),
                "original_bullet": str(bullet.get("original_bullet", "")).strip(),
                "tailored_bullet": str(bullet.get("tailored_bullet", "")).strip(),
                "evidence_used": [item for item in normalized_evidence if item],
                "citations": normalized_citations,
            }
        )

    result["tailored_bullets"] = normalized_bullets

    if source_catalog and any(not bullet["citations"] for bullet in normalized_bullets):
        raise GeneratedContentGroundingError(
            "Generated tailored content did not cite a valid source item."
        )

    supported_numbers = set(NUMBER_PATTERN.findall(grounding_source_text))
    generated_claim_text = "\n".join(
        [result["tailored_summary"]]
        + [bullet["tailored_bullet"] for bullet in normalized_bullets]
    )
    if set(NUMBER_PATTERN.findall(generated_claim_text)) - supported_numbers:
        raise GeneratedContentGroundingError(
            "Generated tailored content contained unsupported numeric claims."
        )

    return result

def build_full_tailored_resume_draft(
    *,
    application: Application,
    resume: Resume,
    tailored_resume,
    project_evidence: list[ProjectEvidence] | None = None,
):
    project_evidence = project_evidence or []
    project_evidence_text = "\n\n".join(
        "\n".join(
            [
                f"Title: {project.title}",
                f"Category: {project.category}",
                f"Description: {project.description}",
                f"Skills: {', '.join(project.skills or [])}",
                f"Keywords: {', '.join(project.keywords or [])}",
                f"Bullets: {' | '.join(project.bullet_bank or [])}",
            ]
        )
        for project in project_evidence
    )
    grounding_source_text = "\n\n".join(
        part for part in [resume.extracted_text, project_evidence_text] if part
    )

    prompt = f"""
You are an expert resume writing assistant.

Build a full tailored resume draft using the structure below.

You must preserve the candidate's core factual content unless tailoring improves wording or ordering:
- keep school, degree, dates, locations, internships, projects, and skills unless there is a strong reason not to
- do not invent new experience
- do not remove important sections like education, experience, projects, or skills
- use the tailored summary and tailored bullets where appropriate
- keep the output ATS-friendly and clean
- the professional summary should be tailored to the application and must be concise, limited to 2 to 3 sentences maximum
- preserve the candidate's factual background from the saved resume and evidence
- only include GPA or coursework if supported by the resume text or evidence
- skill groupings should be relevant to the target role and supported by evidence
- preserve saved tailored skills only when the exact skill is supported by the saved resume or verified project evidence
- omit any tailored skill that cannot be grounded in those sources
- include supported saved tailored skills in the most appropriate skill category

Return JSON only with exactly these keys:
header
professional_summary
education
experience
projects
skills

Rules:
- header must include:
  - name
  - location
  - phone
  - email
  - websites
- education must be a list of objects with:
  - school
  - degree
  - location
  - date_range
  - gpa
  - coursework
- experience must be a list of objects with:
  - title
  - subtitle
  - location
  - date_range
  - bullets
- projects must be a list of objects with:
  - title
  - location
  - date_range
  - bullets
- do not include a subtitle field for projects unless absolutely necessary
- prefer project titles that already contain the needed context
- skills must be an object with:
  - programming_languages
  - frameworks_tools
  - hardware_instrumentation
  - technical_areas
  - developer_tools
- use the tailored bullets where they fit best
- if no tailored bullet applies to a specific entry, keep the original factual content in improved ATS-friendly wording
- do not fabricate metrics
- if a metric is not supported, keep the bullet concrete and achievement-oriented without inventing numbers
- keep resume concise enough to fit a strong one-page student resume when possible
- keep experience and project entries concise
- for most experience and project entries, include 2 to 3 bullets
- use 4 bullets only if the entry is especially relevant to the target role
- prioritize the strongest, most job-relevant bullets and omit weaker or repetitive ones
- do not include filler bullets just to maintain count

Target Application:
Company: {application.company}
Role Title: {application.role_title}
Job Summary: {application.ai_summary or ""}
Required Skills: {application.required_skills or []}
Preferred Skills: {application.preferred_skills or []}
Keywords: {application.keywords or []}
Job Description: {application.job_description or ""}

Saved Resume Text:
{resume.extracted_text}

Saved Resume Analysis:
Summary: {resume.summary}
Strengths: {resume.strengths}
Weaknesses: {resume.weaknesses}
Wording Issues: {resume.wording_issues}
Missing Metrics: {resume.missing_metrics}
Suggested Improvements: {resume.suggested_improvements}

Verified Project Evidence:
{project_evidence_text if project_evidence_text else "No additional project evidence supplied."}

Saved Tailored Resume Content:
Tailored Summary: {tailored_resume.tailored_summary}
Tailored Skills (must preserve these in the final skills section unless exact duplicates): {tailored_resume.tailored_skills}
Tailored Bullets: {tailored_resume.tailored_bullets}
Tailoring Notes: {tailored_resume.tailoring_notes}
"""

    response = client.responses.create(
        model="gpt-5.4-mini",
        input=prompt,
    )

    result = json.loads(response.output_text)

    header = result.get("header", {})
    if not isinstance(header, dict):
        header = {}

    result["header"] = {
        "name": str(header.get("name", "")).strip(),
        "location": header.get("location"),
        "phone": header.get("phone"),
        "email": header.get("email"),
        "websites": header.get("websites", []) if isinstance(header.get("websites", []), list) else [],
    }

    if isinstance(result.get("professional_summary"), list):
        result["professional_summary"] = " ".join(
            str(item).strip() for item in result["professional_summary"] if str(item).strip()
        )

    if result.get("professional_summary") is None:
        result["professional_summary"] = ""

    if not isinstance(result.get("professional_summary"), str):
        result["professional_summary"] = str(result["professional_summary"])
    
    

    if not isinstance(result.get("education"), list):
        result["education"] = []

    normalized_education = []
    for entry in result["education"]:
        if not isinstance(entry, dict):
            continue
        coursework = entry.get("coursework", [])
        if isinstance(coursework, str):
            coursework = [coursework]
        if coursework is None:
            coursework = []

        normalized_education.append(
            {
                "school": str(entry.get("school", "")).strip(),
                "degree": str(entry.get("degree", "")).strip(),
                "location": entry.get("location"),
                "date_range": entry.get("date_range"),
                "gpa": entry.get("gpa"),
                "coursework": [str(item).strip() for item in coursework if str(item).strip()],
            }
        )

    result["education"] = normalized_education

    def normalize_bullet_entries(entries):
        if not isinstance(entries, list):
            return []

        normalized = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue

            bullets = entry.get("bullets", [])
            if isinstance(bullets, str):
                bullets = [bullets]
            if bullets is None:
                bullets = []

            cleaned_bullets = [str(item).strip() for item in bullets if str(item).strip()]
            cleaned_bullets = cleaned_bullets[:4]

            normalized.append(
                {
                    "title": str(entry.get("title", "")).strip(),
                    "subtitle": entry.get("subtitle"),
                    "location": entry.get("location"),
                    "date_range": entry.get("date_range"),
                    "bullets": cleaned_bullets,
                }
            )
        return normalized

    result["experience"] = normalize_bullet_entries(result.get("experience"))
    result["projects"] = normalize_bullet_entries(result.get("projects"))

    skills = result.get("skills", {})
    if not isinstance(skills, dict):
        skills = {}

    def normalize_list(value):
        if isinstance(value, str):
            value = [value]
        if value is None:
            value = []
        if not isinstance(value, list):
            value = []
        return [str(item).strip() for item in value if str(item).strip()]

    model_skill_inputs = []
    for category_values in [
        skills.get("programming_languages"),
        skills.get("frameworks_tools"),
        skills.get("hardware_instrumentation"),
        skills.get("technical_areas"),
        skills.get("developer_tools"),
    ]:
        normalized = normalize_list(category_values)
        model_skill_inputs.extend(normalized)

    all_candidate_skills = []
    all_candidate_skills.extend(model_skill_inputs)
    all_candidate_skills.extend([str(skill).strip() for skill in (tailored_resume.tailored_skills or []) if str(skill).strip()])

    def canonicalize_skill(skill: str) -> str:
        return " ".join(skill.strip().split())

    explicit_evidence_skills = {
        canonicalize_skill(skill).lower()
        for project in project_evidence
        for skill in (project.skills or [])
        if canonicalize_skill(skill)
    }

    def skill_is_grounded(skill: str) -> bool:
        cleaned = canonicalize_skill(skill)
        if not cleaned:
            return False
        if cleaned.lower() in explicit_evidence_skills:
            return True
        pattern = re.compile(
            rf"(?<![A-Za-z0-9]){re.escape(cleaned)}(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        return pattern.search(grounding_source_text) is not None

    programming_languages_set = {
        "c", "c++", "python", "java", "risc-v assembly", "systemverilog",
        "matlab", "javascript", "sql", "r"
    }

    frameworks_tools_set = {
        "vivado", "kicad", "arduino", "docker", "react", "flask",
        "fastapi", "postgresql", "postgreSQL", "celery", "redis"
    }

    hardware_instrumentation_set = {
        "oscilloscope", "function generator", "multimeter",
        "ac/dc power supply", "power supply"
    }

    developer_tools_set = {
        "git", "github", "vs code", "visual studio code",
        "excel", "microsoft office", "word", "powerpoint"
    }

    technical_areas_set = {
        "embedded systems", "fpga design", "digital hardware design",
        "power subsystem design", "analog design", "rtl design",
        "hardware validation", "testing and debugging",
        "device drivers", "interrupt-driven i/o", "firmware development",
        "circuit validation", "hardware prototyping", "equipment testing",
        "data collection and analysis"
    }

    def classify_skill(skill: str) -> str:
        s = canonicalize_skill(skill).lower()

        if s in programming_languages_set:
            return "programming_languages"
        if s in frameworks_tools_set:
            return "frameworks_tools"
        if s in hardware_instrumentation_set:
            return "hardware_instrumentation"
        if s in developer_tools_set:
            return "developer_tools"
        if s in technical_areas_set:
            return "technical_areas"

        if any(token in s for token in ["assembly", "python", "java", "c++", "systemverilog", "sql", "javascript"]):
            return "programming_languages"

        if any(token in s for token in ["vivado", "kicad", "arduino", "docker", "flask", "react", "fastapi", "postgres"]):
            return "frameworks_tools"

        if any(token in s for token in ["oscilloscope", "multimeter", "function generator", "power supply", "instrumentation"]):
            return "hardware_instrumentation"

        if any(token in s for token in ["git", "github", "vs code", "office", "excel", "word", "powerpoint"]):
            return "developer_tools"

        return "technical_areas"

    job_text_parts = [
        application.role_title or "",
        application.ai_summary or "",
        application.job_description or "",
        " ".join(application.required_skills or []),
        " ".join(application.preferred_skills or []),
        " ".join(application.keywords or []),
    ]
    job_text = " ".join(job_text_parts).lower()

    required_skills_lower = [skill.lower() for skill in (application.required_skills or [])]
    preferred_skills_lower = [skill.lower() for skill in (application.preferred_skills or [])]
    keywords_lower = [keyword.lower() for keyword in (application.keywords or [])]
    tailored_skills_lower = [str(skill).strip().lower() for skill in (tailored_resume.tailored_skills or []) if str(skill).strip()]

    def skill_relevance_score(skill: str) -> tuple[int, str]:
        s = canonicalize_skill(skill).lower()
        score = 0

        if s in required_skills_lower:
            score += 100
        elif any(s in req or req in s for req in required_skills_lower):
            score += 80

        if s in preferred_skills_lower:
            score += 60
        elif any(s in pref or pref in s for pref in preferred_skills_lower):
            score += 45

        if s in keywords_lower:
            score += 40
        elif any(s in kw or kw in s for kw in keywords_lower):
            score += 30

        if s in tailored_skills_lower:
            score += 25

        if s in job_text:
            score += 15

        return (-score, s)

    categorized = {
        "programming_languages": [],
        "frameworks_tools": [],
        "hardware_instrumentation": [],
        "technical_areas": [],
        "developer_tools": [],
    }

    seen_global = set()

    for skill in all_candidate_skills:
        cleaned = canonicalize_skill(skill)
        if not cleaned or not skill_is_grounded(cleaned):
            continue

        cleaned_lower = cleaned.lower()
        if cleaned_lower in seen_global:
            continue

        seen_global.add(cleaned_lower)
        category = classify_skill(cleaned)
        categorized[category].append(cleaned)

    for key in categorized:
        categorized[key] = sorted(categorized[key], key=skill_relevance_score)

    result["skills"] = categorized

    supported_numbers = set(NUMBER_PATTERN.findall(grounding_source_text))

    def iter_generated_strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for nested_value in value.values():
                yield from iter_generated_strings(nested_value)
        elif isinstance(value, list):
            for nested_value in value:
                yield from iter_generated_strings(nested_value)

    generated_numbers = {
        number
        for value in iter_generated_strings(result)
        for number in NUMBER_PATTERN.findall(value)
    }
    unsupported_numbers = sorted(generated_numbers - supported_numbers)
    if unsupported_numbers:
        raise GeneratedContentGroundingError(
            "Generated draft contained unsupported numeric claims."
        )

    return result
