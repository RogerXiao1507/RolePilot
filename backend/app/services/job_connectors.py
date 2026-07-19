from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import html
import json
import re
from typing import Any, Protocol
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
import httpx
from xml.etree.ElementTree import ParseError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.discovered_job import DiscoveredJob, JobSourcePosting
from app.services.ai_service import validate_public_job_url


GREENHOUSE_API_ORIGIN = "https://boards-api.greenhouse.io"
LEVER_API_ORIGINS = {
    "global": "https://api.lever.co",
    "eu": "https://api.eu.lever.co",
}
ASHBY_API_ORIGIN = "https://api.ashbyhq.com"
SMARTRECRUITERS_API_ORIGIN = "https://api.smartrecruiters.com"
BOARD_TOKEN_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,120}$")
RAW_PAYLOAD_RETENTION_DAYS = 7


class ConnectorError(RuntimeError):
    """A public source could not be fetched or normalized safely."""


@dataclass(frozen=True)
class NormalizedJob:
    source_name: str
    external_job_id: str
    canonical_url: str
    company_name: str
    title: str
    location: str | None
    description: str
    workplace_type: str | None = None
    employment_type: str | None = None
    seniority_level: str | None = None
    industry: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    source_posted_at: datetime | None = None
    source_updated_at: datetime | None = None
    keywords: tuple[str, ...] = ()
    raw_payload: dict[str, Any] | None = None


class JobConnector(Protocol):
    source_name: str
    source_scope: str

    def fetch_jobs(self) -> list[NormalizedJob]: ...


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def normalize_company_name(value: str | None) -> str:
    normalized = re.sub(r"[^a-z0-9 ]+", " ", normalize_text(value))
    tokens = normalized.split()
    legal_suffixes = {
        "co",
        "company",
        "corp",
        "corporation",
        "gmbh",
        "inc",
        "incorporated",
        "kg",
        "limited",
        "llc",
        "ltd",
        "plc",
        "se",
    }
    while tokens and tokens[-1] in legal_suffixes:
        tokens.pop()
    return " ".join(tokens)


def display_name_from_identifier(value: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[-_]", value) if part)


def description_text(value: str | None) -> str:
    decoded = html.unescape(value or "")
    soup = BeautifulSoup(decoded, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())


def _fingerprint(value: str) -> str:
    return hashlib.sha256(normalize_text(value).encode("utf-8")).hexdigest()


def deduplication_key(job: NormalizedJob) -> str:
    identity = "|".join(
        (
            normalize_company_name(job.company_name),
            normalize_text(job.title),
            normalize_text(job.location),
            _fingerprint(job.description),
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _infer_workplace_type(location: str | None, description: str) -> str | None:
    text = normalize_text(f"{location or ''} {description[:1200]}")
    if re.search(r"\bremote\b", text):
        return "remote"
    if re.search(r"\bhybrid\b", text):
        return "hybrid"
    return None


def _infer_employment_type(title: str, description: str) -> str | None:
    text = normalize_text(f"{title} {description[:1200]}")
    patterns = (
        ("internship", r"\b(intern|internship|co-op)\b"),
        ("contract", r"\b(contract|contractor|temporary)\b"),
        ("part_time", r"\bpart[ -]time\b"),
        ("full_time", r"\bfull[ -]time\b"),
    )
    return next(
        (label for label, pattern in patterns if re.search(pattern, text)), None
    )


def _infer_seniority(title: str) -> str | None:
    text = normalize_text(title)
    patterns = (
        ("intern", r"\b(intern|co-op)\b"),
        ("entry", r"\b(junior|entry|associate|new grad|graduate)\b"),
        ("lead", r"\b(lead|staff|principal)\b"),
        ("manager", r"\b(manager|director|head|vice president|vp)\b"),
        ("senior", r"\b(senior|sr\.?)\b"),
    )
    return next(
        (label for label, pattern in patterns if re.search(pattern, text)), None
    )


def _safe_json_response(
    response: httpx.Response,
    *,
    source_label: str,
    expected_type: type | tuple[type, ...] = dict,
) -> Any:
    if response.status_code != 200:
        raise ConnectorError(f"{source_label} returned an unsuccessful response.")
    media_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if media_type != "application/json":
        raise ConnectorError(f"{source_label} returned an unsupported content type.")
    content_length = response.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.job_discovery_max_response_bytes:
                raise ConnectorError(
                    f"{source_label} returned a response that was too large."
                )
        except ValueError:
            pass
    content = bytearray()
    for chunk in response.iter_bytes():
        content.extend(chunk)
        if len(content) > settings.job_discovery_max_response_bytes:
            raise ConnectorError(
                f"{source_label} returned a response that was too large."
            )
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ConnectorError(f"{source_label} returned invalid JSON.") from exc
    if not isinstance(payload, expected_type):
        raise ConnectorError(f"{source_label} returned an unexpected payload.")
    return payload


def _new_http_client(*, accept: str = "application/json") -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(settings.job_url_timeout_seconds),
        follow_redirects=False,
        trust_env=False,
        headers={
            "Accept": accept,
            "User-Agent": "RolePilot-JobDiscovery/1.0",
        },
    )


def _get_json(
    client: httpx.Client,
    url: str,
    *,
    source_label: str,
    params: dict[str, Any] | None = None,
    expected_type: type | tuple[type, ...] = dict,
) -> Any:
    with client.stream("GET", url, params=params) as response:
        return _safe_json_response(
            response,
            source_label=source_label,
            expected_type=expected_type,
        )


def _safe_xml_response(response: httpx.Response, *, source_label: str):
    if response.status_code != 200:
        raise ConnectorError(f"{source_label} returned an unsuccessful response.")
    media_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if media_type not in {"application/xml", "text/xml"}:
        raise ConnectorError(f"{source_label} returned an unsupported content type.")
    content_length = response.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.job_discovery_max_response_bytes:
                raise ConnectorError(
                    f"{source_label} returned a response that was too large."
                )
        except ValueError:
            pass
    content = bytearray()
    for chunk in response.iter_bytes():
        content.extend(chunk)
        if len(content) > settings.job_discovery_max_response_bytes:
            raise ConnectorError(
                f"{source_label} returned a response that was too large."
            )
    try:
        return ElementTree.fromstring(bytes(content))
    except (ParseError, DefusedXmlException, ValueError) as exc:
        raise ConnectorError(f"{source_label} returned invalid XML.") from exc


def _normalize_workplace_type(value: Any) -> str | None:
    normalized = normalize_text(str(value or "")).replace("_", "").replace("-", "")
    return {
        "remote": "remote",
        "hybrid": "hybrid",
        "onsite": "onsite",
        "onsiteonly": "onsite",
    }.get(normalized)


def _normalize_employment_type(value: Any) -> str | None:
    normalized = normalize_text(str(value or "")).replace("_", "").replace("-", "")
    if normalized in {"fulltime", "permanent", "regular"}:
        return "full_time"
    if normalized in {"parttime"}:
        return "part_time"
    if normalized in {"intern", "internship", "coop"}:
        return "internship"
    if normalized in {"contract", "contractor", "temporary", "temp"}:
        return "contract"
    return None


def _normalize_seniority(value: Any, title: str) -> str | None:
    normalized = normalize_text(str(value or "")).replace("_", " ").replace("-", " ")
    if any(term in normalized for term in ("intern", "student")):
        return "intern"
    if any(term in normalized for term in ("entry", "junior", "graduate")):
        return "entry"
    if any(term in normalized for term in ("manager", "director", "executive")):
        return "manager"
    if any(term in normalized for term in ("lead", "staff", "principal")):
        return "lead"
    if "senior" in normalized:
        return "senior"
    return _infer_seniority(title)


class GreenhouseConnector:
    source_name = "greenhouse"

    def __init__(self, board_token: str, *, client: httpx.Client | None = None):
        token = board_token.strip()
        if not BOARD_TOKEN_PATTERN.fullmatch(token):
            raise ConnectorError("Greenhouse board token is invalid.")
        self.board_token = token
        self.source_scope = token
        self._client = client

    def fetch_jobs(self) -> list[NormalizedJob]:
        owns_client = self._client is None
        client = self._client or _new_http_client()
        try:
            board_url = f"{GREENHOUSE_API_ORIGIN}/v1/boards/{self.board_token}"
            jobs_url = f"{board_url}/jobs"
            board_payload = _get_json(client, board_url, source_label="Greenhouse")
            jobs_payload = _get_json(
                client,
                jobs_url,
                source_label="Greenhouse",
                params={"content": "true"},
            )
        except httpx.HTTPError as exc:
            raise ConnectorError("Greenhouse could not be reached.") from exc
        finally:
            if owns_client:
                client.close()

        company_name = str(board_payload.get("name") or self.board_token).strip()
        raw_jobs = jobs_payload.get("jobs")
        if not isinstance(raw_jobs, list):
            raise ConnectorError("Greenhouse jobs payload is missing its job list.")
        if len(raw_jobs) > settings.job_discovery_max_jobs_per_board:
            raise ConnectorError("Greenhouse board exceeds the configured job limit.")

        jobs: list[NormalizedJob] = []
        for payload in raw_jobs:
            if not isinstance(payload, dict):
                raise ConnectorError("Greenhouse returned an unexpected job record.")
            title = str(payload.get("title") or "").strip()
            canonical_url = str(payload.get("absolute_url") or "").strip()
            if payload.get("id") is None or not title or not canonical_url:
                raise ConnectorError("Greenhouse returned an incomplete job record.")
            parsed_url = urlsplit(canonical_url)
            if parsed_url.scheme not in {"http", "https"}:
                continue
            description = description_text(payload.get("content"))
            location_payload = payload.get("location")
            location = (
                str(location_payload.get("name") or "").strip() or None
                if isinstance(location_payload, dict)
                else None
            )
            # Greenhouse exposes updated_at, not a guaranteed original posting date.
            # Preserve it separately and leave source_posted_at unknown.
            jobs.append(
                NormalizedJob(
                    source_name=self.source_name,
                    external_job_id=f"{self.board_token}:{payload['id']}",
                    canonical_url=canonical_url,
                    company_name=company_name,
                    title=title,
                    location=location,
                    description=description,
                    workplace_type=_infer_workplace_type(location, description),
                    employment_type=_infer_employment_type(title, description),
                    seniority_level=_infer_seniority(title),
                    source_posted_at=None,
                    source_updated_at=_parse_datetime(payload.get("updated_at")),
                    raw_payload=payload,
                )
            )
        return jobs


def _integer_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return None


def _keyword_values(*values: Any) -> tuple[str, ...]:
    keywords: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            keywords.append(cleaned)
            seen.add(key)
    return tuple(keywords)


class LeverConnector:
    source_name = "lever"

    def __init__(
        self,
        site: str,
        *,
        company_name: str | None = None,
        region: str = "global",
        client: httpx.Client | None = None,
    ):
        normalized_site = site.strip()
        if not BOARD_TOKEN_PATTERN.fullmatch(normalized_site):
            raise ConnectorError("Lever site is invalid.")
        if region not in LEVER_API_ORIGINS:
            raise ConnectorError("Lever region must be global or eu.")
        self.site = normalized_site
        self.region = region
        self.company_name = (company_name or display_name_from_identifier(site)).strip()
        self.source_scope = f"{region}:{normalized_site}"
        self._client = client

    def fetch_jobs(self) -> list[NormalizedJob]:
        owns_client = self._client is None
        client = self._client or _new_http_client()
        raw_jobs: list[dict[str, Any]] = []
        base_url = f"{LEVER_API_ORIGINS[self.region]}/v0/postings/{self.site}"
        try:
            while True:
                remaining = (
                    settings.job_discovery_max_jobs_per_board + 1 - len(raw_jobs)
                )
                page_limit = min(100, remaining)
                if page_limit <= 0:
                    raise ConnectorError(
                        "Lever board exceeds the configured job limit."
                    )
                page = _get_json(
                    client,
                    base_url,
                    source_label="Lever",
                    params={
                        "mode": "json",
                        "skip": len(raw_jobs),
                        "limit": page_limit,
                    },
                    expected_type=list,
                )
                if not all(isinstance(item, dict) for item in page):
                    raise ConnectorError("Lever returned an unexpected job record.")
                raw_jobs.extend(page)
                if len(raw_jobs) > settings.job_discovery_max_jobs_per_board:
                    raise ConnectorError(
                        "Lever board exceeds the configured job limit."
                    )
                if len(page) < page_limit:
                    break
        except httpx.HTTPError as exc:
            raise ConnectorError("Lever could not be reached.") from exc
        finally:
            if owns_client:
                client.close()

        jobs: list[NormalizedJob] = []
        for payload in raw_jobs:
            posting_id = payload.get("id")
            title = str(payload.get("text") or "").strip()
            canonical_url = str(payload.get("hostedUrl") or "").strip()
            if posting_id is None or not title or not canonical_url:
                raise ConnectorError("Lever returned an incomplete job record.")
            categories = payload.get("categories")
            if not isinstance(categories, dict):
                categories = {}
            location = str(categories.get("location") or "").strip() or None
            description = str(payload.get("descriptionPlain") or "").strip()
            if not description:
                description = description_text(payload.get("description"))
            extra_sections: list[str] = []
            raw_lists = payload.get("lists")
            if isinstance(raw_lists, list):
                for section in raw_lists:
                    if not isinstance(section, dict):
                        continue
                    section_title = str(section.get("text") or "").strip()
                    section_content = description_text(section.get("content"))
                    if section_title or section_content:
                        extra_sections.append(
                            " ".join(
                                part
                                for part in (section_title, section_content)
                                if part
                            )
                        )
            additional = str(payload.get("additionalPlain") or "").strip()
            description = " ".join(
                part for part in (description, *extra_sections, additional) if part
            )
            salary = payload.get("salaryRange")
            if not isinstance(salary, dict):
                salary = {}
            workplace_type = _normalize_workplace_type(payload.get("workplaceType"))
            employment_type = _normalize_employment_type(categories.get("commitment"))
            jobs.append(
                NormalizedJob(
                    source_name=self.source_name,
                    external_job_id=f"{self.source_scope}:{posting_id}",
                    canonical_url=canonical_url,
                    company_name=self.company_name,
                    title=title,
                    location=location,
                    description=description,
                    workplace_type=workplace_type
                    or _infer_workplace_type(location, description),
                    employment_type=employment_type
                    or _infer_employment_type(title, description),
                    seniority_level=_normalize_seniority(
                        categories.get("level"), title
                    ),
                    salary_min=_integer_or_none(salary.get("min")),
                    salary_max=_integer_or_none(salary.get("max")),
                    salary_currency=(
                        str(salary.get("currency") or "").upper()[:3] or None
                    ),
                    source_posted_at=None,
                    source_updated_at=None,
                    keywords=_keyword_values(
                        categories.get("team"), categories.get("department")
                    ),
                    raw_payload=payload,
                )
            )
        return jobs


def _ashby_salary(payload: dict[str, Any]) -> tuple[int | None, int | None, str | None]:
    compensation = payload.get("compensation")
    if not isinstance(compensation, dict):
        return None, None, None
    components = compensation.get("summaryComponents")
    if not isinstance(components, list):
        return None, None, None
    salary_components = [
        component
        for component in components
        if isinstance(component, dict)
        and component.get("compensationType") == "Salary"
        and component.get("interval") == "1 YEAR"
    ]
    currencies = {
        str(component.get("currencyCode") or "").upper()
        for component in salary_components
        if component.get("currencyCode")
    }
    if len(currencies) != 1:
        return None, None, None
    minimums = [
        value
        for component in salary_components
        if (value := _integer_or_none(component.get("minValue"))) is not None
    ]
    maximums = [
        value
        for component in salary_components
        if (value := _integer_or_none(component.get("maxValue"))) is not None
    ]
    return (
        min(minimums) if minimums else None,
        max(maximums) if maximums else None,
        next(iter(currencies)),
    )


class AshbyConnector:
    source_name = "ashby"

    def __init__(
        self,
        board_name: str,
        *,
        company_name: str | None = None,
        client: httpx.Client | None = None,
    ):
        normalized_board = board_name.strip()
        if not BOARD_TOKEN_PATTERN.fullmatch(normalized_board):
            raise ConnectorError("Ashby board name is invalid.")
        self.board_name = normalized_board
        self.company_name = (
            company_name or display_name_from_identifier(board_name)
        ).strip()
        self.source_scope = normalized_board
        self._client = client

    def fetch_jobs(self) -> list[NormalizedJob]:
        owns_client = self._client is None
        client = self._client or _new_http_client()
        endpoint = f"{ASHBY_API_ORIGIN}/posting-api/job-board/{self.board_name}"
        try:
            response_payload = _get_json(
                client,
                endpoint,
                source_label="Ashby",
                params={"includeCompensation": "true"},
            )
        except httpx.HTTPError as exc:
            raise ConnectorError("Ashby could not be reached.") from exc
        finally:
            if owns_client:
                client.close()
        raw_jobs = response_payload.get("jobs")
        if not isinstance(raw_jobs, list):
            raise ConnectorError("Ashby jobs payload is missing its job list.")
        if len(raw_jobs) > settings.job_discovery_max_jobs_per_board:
            raise ConnectorError("Ashby board exceeds the configured job limit.")

        jobs: list[NormalizedJob] = []
        for payload in raw_jobs:
            if not isinstance(payload, dict):
                raise ConnectorError("Ashby returned an unexpected job record.")
            if payload.get("isListed") is not True:
                continue
            posting_id = payload.get("id")
            title = str(payload.get("title") or "").strip()
            canonical_url = str(payload.get("jobUrl") or "").strip()
            if posting_id is None or not title or not canonical_url:
                raise ConnectorError("Ashby returned an incomplete listed job record.")
            location = str(payload.get("location") or "").strip() or None
            description = str(payload.get("descriptionPlain") or "").strip()
            if not description:
                description = description_text(payload.get("descriptionHtml"))
            salary_min, salary_max, salary_currency = _ashby_salary(payload)
            workplace_type = _normalize_workplace_type(payload.get("workplaceType"))
            if workplace_type is None and payload.get("isRemote") is True:
                workplace_type = "remote"
            jobs.append(
                NormalizedJob(
                    source_name=self.source_name,
                    external_job_id=f"{self.source_scope}:{posting_id}",
                    canonical_url=canonical_url,
                    company_name=self.company_name,
                    title=title,
                    location=location,
                    description=description,
                    workplace_type=workplace_type
                    or _infer_workplace_type(location, description),
                    employment_type=_normalize_employment_type(
                        payload.get("employmentType")
                    )
                    or _infer_employment_type(title, description),
                    seniority_level=_infer_seniority(title),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency=salary_currency,
                    source_posted_at=_parse_datetime(payload.get("publishedAt")),
                    source_updated_at=None,
                    keywords=_keyword_values(
                        payload.get("department"), payload.get("team")
                    ),
                    raw_payload=payload,
                )
            )
        return jobs


def _smartrecruiters_description(payload: dict[str, Any]) -> str:
    job_ad = payload.get("jobAd")
    sections = job_ad.get("sections") if isinstance(job_ad, dict) else None
    if not isinstance(sections, dict):
        return ""
    parts: list[str] = []
    for section_name in ("jobDescription", "qualifications", "additionalInformation"):
        section = sections.get(section_name)
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or "").strip()
        body = description_text(section.get("text"))
        if title or body:
            parts.append(" ".join(part for part in (title, body) if part))
    return " ".join(parts)


class SmartRecruitersConnector:
    source_name = "smartrecruiters"

    def __init__(
        self,
        company_identifier: str,
        *,
        company_name: str | None = None,
        client: httpx.Client | None = None,
    ):
        identifier = company_identifier.strip()
        if not BOARD_TOKEN_PATTERN.fullmatch(identifier):
            raise ConnectorError("SmartRecruiters company identifier is invalid.")
        self.company_identifier = identifier
        self.company_name = company_name.strip() if company_name else None
        self.source_scope = identifier
        self._client = client

    def fetch_jobs(self) -> list[NormalizedJob]:
        owns_client = self._client is None
        client = self._client or _new_http_client()
        base_url = (
            f"{SMARTRECRUITERS_API_ORIGIN}/v1/companies/"
            f"{self.company_identifier}/postings"
        )
        summaries: list[dict[str, Any]] = []
        total_found: int | None = None
        try:
            while total_found is None or len(summaries) < total_found:
                page = _get_json(
                    client,
                    base_url,
                    source_label="SmartRecruiters",
                    params={"offset": len(summaries), "limit": 100},
                )
                raw_content = page.get("content")
                if not isinstance(raw_content, list) or not all(
                    isinstance(item, dict) for item in raw_content
                ):
                    raise ConnectorError(
                        "SmartRecruiters payload is missing its posting list."
                    )
                parsed_total = _integer_or_none(page.get("totalFound"))
                if parsed_total is None:
                    raise ConnectorError(
                        "SmartRecruiters payload is missing totalFound."
                    )
                total_found = parsed_total
                if total_found > settings.job_discovery_max_jobs_per_board:
                    raise ConnectorError(
                        "SmartRecruiters board exceeds the configured job limit."
                    )
                summaries.extend(raw_content)
                if len(summaries) > total_found:
                    raise ConnectorError(
                        "SmartRecruiters returned more postings than totalFound."
                    )
                if not raw_content and len(summaries) < total_found:
                    raise ConnectorError(
                        "SmartRecruiters pagination ended before all postings were returned."
                    )

            jobs: list[NormalizedJob] = []
            for summary in summaries:
                posting_id = summary.get("id") or summary.get("uuid")
                if posting_id is None:
                    continue
                detail = _get_json(
                    client,
                    f"{base_url}/{posting_id}",
                    source_label="SmartRecruiters",
                )
                if detail.get("active") is False:
                    continue
                if summary.get("visibility") not in {None, "PUBLIC"}:
                    continue
                title = str(detail.get("name") or summary.get("name") or "").strip()
                canonical_url = str(detail.get("applyUrl") or "").strip()
                description = _smartrecruiters_description(detail)
                if not title or not canonical_url or not description:
                    raise ConnectorError(
                        "SmartRecruiters returned an incomplete public posting."
                    )
                company = detail.get("company")
                summary_company = summary.get("company")
                source_company_name = None
                if isinstance(company, dict):
                    source_company_name = company.get("name")
                if not source_company_name and isinstance(summary_company, dict):
                    source_company_name = summary_company.get("name")
                resolved_company = (
                    self.company_name
                    or str(
                        source_company_name
                        or display_name_from_identifier(self.company_identifier)
                    ).strip()
                )
                location_payload = detail.get("location")
                if not isinstance(location_payload, dict):
                    location_payload = summary.get("location")
                if not isinstance(location_payload, dict):
                    location_payload = {}
                location = str(location_payload.get("fullLocation") or "").strip()
                if not location:
                    location = ", ".join(
                        str(location_payload.get(field) or "").strip()
                        for field in ("city", "region", "country")
                        if location_payload.get(field)
                    )
                workplace_type = None
                if location_payload.get("hybrid") is True:
                    workplace_type = "hybrid"
                elif location_payload.get("remote") is True:
                    workplace_type = "remote"
                employment = detail.get("typeOfEmployment") or summary.get(
                    "typeOfEmployment"
                )
                experience = detail.get("experienceLevel") or summary.get(
                    "experienceLevel"
                )
                industry = detail.get("industry") or summary.get("industry")
                department = detail.get("department") or summary.get("department")
                function = detail.get("function") or summary.get("function")
                employment_label = (
                    employment.get("label")
                    if isinstance(employment, dict)
                    else employment
                )
                experience_label = (
                    experience.get("label")
                    if isinstance(experience, dict)
                    else experience
                )
                industry_label = (
                    industry.get("label") if isinstance(industry, dict) else industry
                )
                department_label = (
                    department.get("label")
                    if isinstance(department, dict)
                    else department
                )
                function_label = (
                    function.get("label") if isinstance(function, dict) else function
                )
                jobs.append(
                    NormalizedJob(
                        source_name=self.source_name,
                        external_job_id=f"{self.source_scope}:{posting_id}",
                        canonical_url=canonical_url,
                        company_name=resolved_company,
                        title=title,
                        location=location or None,
                        description=description,
                        workplace_type=workplace_type
                        or _infer_workplace_type(location, description),
                        employment_type=_normalize_employment_type(employment_label)
                        or _infer_employment_type(title, description),
                        seniority_level=_normalize_seniority(experience_label, title),
                        industry=(
                            str(industry_label).strip() if industry_label else None
                        ),
                        source_posted_at=_parse_datetime(
                            detail.get("releasedDate") or summary.get("releasedDate")
                        ),
                        source_updated_at=None,
                        keywords=_keyword_values(department_label, function_label),
                        raw_payload={"summary": summary, "detail": detail},
                    )
                )
        except httpx.HTTPError as exc:
            raise ConnectorError("SmartRecruiters could not be reached.") from exc
        finally:
            if owns_client:
                client.close()
        return jobs


class PersonioConnector:
    source_name = "personio"

    def __init__(
        self,
        account: str,
        *,
        company_name: str | None = None,
        domain: str = "com",
        job_url_template: str | None = None,
        client: httpx.Client | None = None,
    ):
        normalized_account = account.strip()
        if not BOARD_TOKEN_PATTERN.fullmatch(normalized_account):
            raise ConnectorError("Personio account is invalid.")
        if domain not in {"com", "de"}:
            raise ConnectorError("Personio domain must be com or de.")
        if job_url_template is not None and (
            not job_url_template.startswith("https://")
            or "{id}" not in job_url_template
        ):
            raise ConnectorError(
                "Personio job URL template must be HTTPS and contain {id}."
            )
        self.account = normalized_account
        self.company_name = company_name.strip() if company_name else None
        self.domain = domain
        self.job_url_template = job_url_template
        self.source_scope = f"{domain}:{normalized_account}"
        self._client = client

    def fetch_jobs(self) -> list[NormalizedJob]:
        owns_client = self._client is None
        client = self._client or _new_http_client(
            accept="application/xml,text/xml;q=0.9"
        )
        endpoint = f"https://{self.account}.jobs.personio.{self.domain}/xml"
        try:
            with client.stream("GET", endpoint, params={"language": "en"}) as response:
                root = _safe_xml_response(response, source_label="Personio")
        except httpx.HTTPError as exc:
            raise ConnectorError("Personio could not be reached.") from exc
        finally:
            if owns_client:
                client.close()

        positions = list(root.findall("position"))
        if len(positions) > settings.job_discovery_max_jobs_per_board:
            raise ConnectorError("Personio feed exceeds the configured job limit.")
        jobs: list[NormalizedJob] = []
        for position in positions:
            posting_id = (position.findtext("id") or "").strip()
            title = (position.findtext("name") or "").strip()
            if not posting_id or not title:
                raise ConnectorError("Personio returned an incomplete position.")
            description_parts: list[str] = []
            descriptions = position.find("jobDescriptions")
            if descriptions is not None:
                for section in descriptions.findall("jobDescription"):
                    section_title = (section.findtext("name") or "").strip()
                    section_body = description_text(section.findtext("value"))
                    if section_title or section_body:
                        description_parts.append(
                            " ".join(
                                part for part in (section_title, section_body) if part
                            )
                        )
            description = " ".join(description_parts)
            if not description:
                raise ConnectorError(
                    "Personio returned a published position without a description."
                )
            locations = [(position.findtext("office") or "").strip()]
            additional_offices = position.find("additionalOffices")
            if additional_offices is not None:
                locations.extend(
                    (office.text or "").strip()
                    for office in additional_offices.findall("office")
                )
            location = ", ".join(dict.fromkeys(item for item in locations if item))
            template = self.job_url_template or (
                f"https://{self.account}.jobs.personio.{self.domain}/job/{{id}}"
                "?display=en"
            )
            canonical_url = template.replace("{id}", posting_id)
            source_company = (position.findtext("subcompany") or "").strip()
            resolved_company = (
                self.company_name
                or source_company
                or (display_name_from_identifier(self.account))
            )
            employment_value = position.findtext("schedule") or position.findtext(
                "employmentType"
            )
            seniority_value = position.findtext("seniority")
            jobs.append(
                NormalizedJob(
                    source_name=self.source_name,
                    external_job_id=f"{self.source_scope}:{posting_id}",
                    canonical_url=canonical_url,
                    company_name=resolved_company,
                    title=title,
                    location=location[:400] or None,
                    description=description,
                    workplace_type=_infer_workplace_type(location, description),
                    employment_type=_normalize_employment_type(employment_value)
                    or _infer_employment_type(title, description),
                    seniority_level=_normalize_seniority(seniority_value, title),
                    source_posted_at=None,
                    source_updated_at=None,
                    keywords=_keyword_values(
                        position.findtext("department"),
                        position.findtext("recruitingCategory"),
                        position.findtext("occupation"),
                    ),
                    raw_payload={
                        child.tag: child.text
                        for child in position
                        if child.tag not in {"jobDescriptions"}
                    },
                )
            )
        return jobs


def configured_connectors() -> list[JobConnector]:
    connectors: list[JobConnector] = []
    if settings.job_discovery_greenhouse_enabled:
        connectors.extend(
            GreenhouseConnector(board_token)
            for board_token in settings.job_discovery_greenhouse_boards
        )
    if settings.job_discovery_lever_enabled:
        connectors.extend(
            LeverConnector(
                board.site,
                company_name=board.company_name,
                region=board.region,
            )
            for board in settings.job_discovery_lever_boards
        )
    if settings.job_discovery_ashby_enabled:
        connectors.extend(
            AshbyConnector(
                board.identifier,
                company_name=board.company_name,
            )
            for board in settings.job_discovery_ashby_boards
        )
    if settings.job_discovery_smartrecruiters_enabled:
        connectors.extend(
            SmartRecruitersConnector(
                board.identifier,
                company_name=board.company_name,
            )
            for board in settings.job_discovery_smartrecruiters_boards
        )
    if settings.job_discovery_personio_enabled:
        connectors.extend(
            PersonioConnector(
                board.account,
                company_name=board.company_name,
                domain=board.domain,
                job_url_template=board.job_url_template,
            )
            for board in settings.job_discovery_personio_boards
        )
    return connectors


def upsert_normalized_job(
    db: Session, normalized: NormalizedJob, *, now: datetime | None = None
) -> tuple[DiscoveredJob, JobSourcePosting, bool]:
    observed_at = now or datetime.now(timezone.utc)
    canonical_url = validate_public_job_url(normalized.canonical_url)
    source = db.scalar(
        select(JobSourcePosting).where(
            JobSourcePosting.source_name == normalized.source_name,
            JobSourcePosting.external_job_id == normalized.external_job_id,
        )
    )
    created = source is None
    key = deduplication_key(normalized)
    description_fingerprint = _fingerprint(normalized.description)

    if source is None:
        canonical_source = db.scalar(
            select(JobSourcePosting)
            .where(JobSourcePosting.canonical_url == canonical_url)
            .order_by(JobSourcePosting.first_seen_at.asc())
            .limit(1)
        )
        job = (
            db.get(DiscoveredJob, canonical_source.discovered_job_id)
            if canonical_source is not None
            else None
        )
        if job is None:
            job = db.scalar(
                select(DiscoveredJob)
                .where(DiscoveredJob.deduplication_key == key)
                .order_by(DiscoveredJob.first_seen_at.asc())
                .limit(1)
            )
        if job is None:
            job = DiscoveredJob(
                company_name=normalized.company_name,
                company_normalized=normalize_company_name(normalized.company_name),
                title=normalized.title,
                title_normalized=normalize_text(normalized.title),
                location=normalized.location,
                location_normalized=normalize_text(normalized.location) or None,
                workplace_type=normalized.workplace_type,
                employment_type=normalized.employment_type,
                seniority_level=normalized.seniority_level,
                industry=normalized.industry,
                salary_min=normalized.salary_min,
                salary_max=normalized.salary_max,
                salary_currency=normalized.salary_currency,
                description=normalized.description,
                description_fingerprint=description_fingerprint,
                deduplication_key=key,
                keywords=list(normalized.keywords),
                source_posted_at=normalized.source_posted_at,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
                verification_status="active",
            )
            db.add(job)
            db.flush()
        source = JobSourcePosting(
            discovered_job_id=job.id,
            source_name=normalized.source_name,
            external_job_id=normalized.external_job_id,
            canonical_url=canonical_url,
            first_seen_at=observed_at,
        )
        db.add(source)
    else:
        job = db.get(DiscoveredJob, source.discovered_job_id)
        if job is None:
            raise ConnectorError(
                "A source posting references a missing discovered job."
            )

    job.company_name = normalized.company_name
    job.company_normalized = normalize_company_name(normalized.company_name)
    job.title = normalized.title
    job.title_normalized = normalize_text(normalized.title)
    job.location = normalized.location
    job.location_normalized = normalize_text(normalized.location) or None
    job.workplace_type = normalized.workplace_type
    job.employment_type = normalized.employment_type
    job.seniority_level = normalized.seniority_level
    job.industry = normalized.industry
    job.salary_min = normalized.salary_min
    job.salary_max = normalized.salary_max
    job.salary_currency = normalized.salary_currency
    job.description = normalized.description
    job.description_fingerprint = description_fingerprint
    job.deduplication_key = key
    job.keywords = list(normalized.keywords)
    if normalized.source_posted_at is not None and (
        job.source_posted_at is None
        or normalized.source_posted_at < job.source_posted_at
    ):
        job.source_posted_at = normalized.source_posted_at
    job.last_seen_at = observed_at
    job.verification_status = "active"

    source.canonical_url = canonical_url
    source.source_posted_at = normalized.source_posted_at
    source.source_updated_at = normalized.source_updated_at
    source.last_seen_at = observed_at
    source.last_verified_at = observed_at
    source.verification_status = "active"
    source.raw_payload = normalized.raw_payload or {}
    source.raw_payload_expires_at = observed_at + timedelta(
        days=RAW_PAYLOAD_RETENTION_DAYS
    )
    db.flush()
    return job, source, created


def sync_connector(db: Session, connector: JobConnector) -> dict[str, int]:
    jobs = connector.fetch_jobs()
    observed_at = datetime.now(timezone.utc)
    seen_ids: set[str] = set()
    created = 0
    for normalized in jobs:
        _, _, was_created = upsert_normalized_job(db, normalized, now=observed_at)
        seen_ids.add(normalized.external_job_id)
        created += int(was_created)

    escaped_scope = (
        connector.source_scope.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    active_sources = db.scalars(
        select(JobSourcePosting).where(
            JobSourcePosting.source_name == connector.source_name,
            JobSourcePosting.external_job_id.like(f"{escaped_scope}:%", escape="\\"),
            JobSourcePosting.verification_status == "active",
        )
    ).all()
    removed = 0
    affected_job_ids: set = set()
    for source in active_sources:
        if source.external_job_id in seen_ids:
            continue
        source.verification_status = "removed"
        source.last_verified_at = observed_at
        affected_job_ids.add(source.discovered_job_id)
        removed += 1

    # SessionLocal disables autoflush; persist source status changes before the
    # active-source query decides whether the normalized role is still live.
    db.flush()
    for job_id in affected_job_ids:
        has_active_source = db.scalar(
            select(JobSourcePosting.id).where(
                JobSourcePosting.discovered_job_id == job_id,
                JobSourcePosting.verification_status == "active",
            )
        )
        if not has_active_source:
            job = db.get(DiscoveredJob, job_id)
            if job:
                job.verification_status = "removed"

    db.execute(
        update(JobSourcePosting)
        .where(JobSourcePosting.raw_payload_expires_at < observed_at)
        .values(raw_payload={}, raw_payload_expires_at=None)
    )
    db.commit()
    return {"seen": len(jobs), "created": created, "removed": removed}
