import hashlib
import json
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_full_resume_draft import ApplicationFullResumeDraft
from app.models.application_resume_match import ApplicationResumeMatch
from app.models.application_tailored_resume import ApplicationTailoredResume
from app.models.resume import Resume
from app.models.resume_source_item import ResumeSourceItem


def content_fingerprint(value: object) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def resume_fingerprint(*, extracted_text: str, structured_data: dict) -> str:
    return content_fingerprint(
        {
            "extracted_text": "\n".join(extracted_text.split()),
            "structured_data": structured_data,
        }
    )


def flatten_resume_source_items(structured_data: dict) -> list[dict]:
    items: list[dict] = []
    ordinals: defaultdict[tuple[str, str], int] = defaultdict(int)

    def add(
        section: str,
        item_type: str,
        content: str | None,
        *,
        title: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        normalized = " ".join(str(content or "").split())
        if not normalized:
            return
        key = (section, item_type)
        ordinal = ordinals[key]
        ordinals[key] += 1
        items.append(
            {
                "section": section,
                "item_type": item_type,
                "title": title,
                "content": normalized,
                "ordinal": ordinal,
                "source_metadata": metadata or {},
            }
        )

    contact = structured_data.get("contact") or {}
    for field in ("name", "email", "phone", "location"):
        add("contact", field, contact.get(field), title=field.replace("_", " ").title())
    for link in contact.get("links") or []:
        add("contact", "link", link, title="Link")

    for section in ("education", "experience", "projects", "other"):
        for entry_index, entry in enumerate(structured_data.get(section) or []):
            title = str(entry.get("title") or section.title()).strip()
            header_parts = [
                title,
                entry.get("subtitle"),
                entry.get("location"),
                entry.get("date_range"),
            ]
            add(
                section,
                "entry",
                " | ".join(str(part).strip() for part in header_parts if part),
                title=title,
                metadata={"entry_index": entry_index},
            )
            for bullet_index, bullet in enumerate(entry.get("bullets") or []):
                add(
                    section,
                    "bullet",
                    bullet,
                    title=title,
                    metadata={
                        "entry_index": entry_index,
                        "bullet_index": bullet_index,
                    },
                )

    for skill in structured_data.get("skills") or []:
        add("skills", "skill", skill, title="Skills")

    return items


def sync_resume_source_items(db: Session, *, resume: Resume) -> list[ResumeSourceItem]:
    existing = db.scalars(
        select(ResumeSourceItem).where(
            ResumeSourceItem.user_id == resume.user_id,
            ResumeSourceItem.resume_id == resume.id,
        )
    ).all()
    existing_by_position = {
        (item.section, item.item_type, item.ordinal): item for item in existing
    }
    existing_by_content: defaultdict[tuple[str, str, str], list[ResumeSourceItem]] = defaultdict(list)
    for item in existing:
        existing_by_content[(item.section, item.item_type, item.content)].append(item)
    touched_ids = set()
    active_items: list[ResumeSourceItem] = []

    flattened = flatten_resume_source_items(resume.structured_data or {})
    if not flattened:
        flattened = [
            {
                "section": "other",
                "item_type": "document",
                "title": resume.label,
                "content": " ".join(resume.extracted_text.split()),
                "ordinal": 0,
                "source_metadata": {"fallback": "raw_extracted_text"},
            }
        ]

    exact_matches_by_position: dict[tuple[str, str, int], ResumeSourceItem] = {}
    reserved_exact_ids = set()
    for value in flattened:
        position = (value["section"], value["item_type"], value["ordinal"])
        content_key = (value["section"], value["item_type"], value["content"])
        exact_match = next(
            (
                candidate
                for candidate in existing_by_content.get(content_key, [])
                if candidate.id not in reserved_exact_ids
            ),
            None,
        )
        if exact_match is not None:
            exact_matches_by_position[position] = exact_match
            reserved_exact_ids.add(exact_match.id)

    for value in flattened:
        position = (value["section"], value["item_type"], value["ordinal"])
        item = exact_matches_by_position.get(position)
        if item is None:
            positional_candidate = existing_by_position.get(position)
            if (
                positional_candidate is not None
                and positional_candidate.id not in touched_ids
                and positional_candidate.id not in reserved_exact_ids
            ):
                item = positional_candidate
        if item is None:
            item = ResumeSourceItem(
                user_id=resume.user_id,
                resume_id=resume.id,
                source_version=resume.version,
                is_user_verified=True,
                is_active=True,
                **value,
            )
            db.add(item)
        else:
            item.source_version = resume.version
            item.section = value["section"]
            item.item_type = value["item_type"]
            item.title = value["title"]
            item.content = value["content"]
            item.ordinal = value["ordinal"]
            item.source_metadata = value["source_metadata"]
            item.is_active = True
        if item.id is not None:
            touched_ids.add(item.id)
        active_items.append(item)

    for item in existing:
        if item.id not in touched_ids:
            item.source_version = resume.version
            item.is_active = False

    db.flush()
    return active_items


def mark_resume_artifacts_stale(db: Session, *, resume: Resume) -> None:
    for model in (
        ApplicationResumeMatch,
        ApplicationTailoredResume,
        ApplicationFullResumeDraft,
    ):
        db.query(model).filter(
            model.user_id == resume.user_id,
            model.resume_id == resume.id,
        ).update({"is_stale": True}, synchronize_session=False)


def mark_application_artifacts_stale(db: Session, *, user_id, application_id: int) -> None:
    for model in (
        ApplicationResumeMatch,
        ApplicationTailoredResume,
        ApplicationFullResumeDraft,
    ):
        db.query(model).filter(
            model.user_id == user_id,
            model.application_id == application_id,
        ).update({"is_stale": True}, synchronize_session=False)
