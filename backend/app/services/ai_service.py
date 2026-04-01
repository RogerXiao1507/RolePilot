import json
import httpx
from bs4 import BeautifulSoup
from openai import OpenAI

from app.core.config import settings
from app.models.application import Application
from app.models.project_evidence import ProjectEvidence
from app.models.resume import Resume
from sqlalchemy.orm import Session
from app.services.retrieval_service import retrieve_relevant_chunks_for_application
from app.models.project_evidence_chunk import ProjectEvidenceChunk
from app.models.application_tailored_resume import ApplicationTailoredResume

client = OpenAI(api_key=settings.openai_api_key)


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


def extract_text_from_url(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    response = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

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
    relevant_chunks = retrieve_relevant_chunks_for_application(
        db=db,
        application=application,
        top_k=5,
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
- section should be something like "Projects", "Research", "Experience", or "Skills"
- source_title should identify the project, role, or source area the bullet comes from
- original_bullet should identify the resume or project bullet that should be replaced
- tailored_bullet should be the improved replacement bullet
- evidence_used should be a short list naming the specific source evidence used, such as project titles or "Saved Resume"
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

    result["tailored_skills"] = [skill for skill in normalized_skills if skill]

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

        normalized_bullets.append(
            {
                "section": str(bullet.get("section", "Projects")).strip(),
                "source_title": str(bullet.get("source_title", "Saved Resume")).strip(),
                "original_bullet": str(bullet.get("original_bullet", "")).strip(),
                "tailored_bullet": str(bullet.get("tailored_bullet", "")).strip(),
                "evidence_used": [item for item in normalized_evidence if item],
            }
        )

    result["tailored_bullets"] = normalized_bullets

    print("TAILOR RESULT:")
    print(result)

    return result

def build_full_tailored_resume_draft(
    *,
    application: Application,
    resume: Resume,
    tailored_resume,
):
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
- all saved tailored skills must be preserved in the final skills section unless they are exact duplicates
- do not omit saved tailored skills just because they overlap semantically with another skill
- include the saved tailored skills in the most appropriate skill category

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

    original_resume_skill_inputs = []
    for maybe_list in [
        ["C++", "C", "Python", "Java", "RISC-V Assembly", "SystemVerilog"],
        ["KiCad", "Vivado", "Arduino", "MATLAB"],
        ["Oscilloscope", "Function Generator", "Multimeter", "AC/DC Power Supply"],
        ["FPGA Design", "Digital Hardware Design", "Power Subsystem Design", "Analog Design", "RTL Design", "Embedded Systems"],
        ["Git", "GitHub", "VS Code", "Excel", "Microsoft Office"],
    ]:
        original_resume_skill_inputs.extend(maybe_list)

    all_candidate_skills.extend(original_resume_skill_inputs)

    def canonicalize_skill(skill: str) -> str:
        return " ".join(skill.strip().split())

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
        if not cleaned:
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

    return result