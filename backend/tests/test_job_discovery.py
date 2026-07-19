from datetime import datetime, timedelta, timezone
from uuid import uuid4
from contextlib import contextmanager

from fastapi.testclient import TestClient
import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.database import SessionLocal
from app.core.config import (
    LeverBoardConfig,
    PersonioBoardConfig,
    PublicATSBoardConfig,
    settings,
)
from app.main import app
from app.models.discovered_job import DiscoveredJob, JobSourcePosting
from app.models.job_search import JobSearch
from app.models.user import User
from app.services.job_connectors import (
    ConnectorError,
    AshbyConnector,
    GreenhouseConnector,
    LeverConnector,
    NormalizedJob,
    PersonioConnector,
    SmartRecruitersConnector,
    description_text,
    configured_connectors,
    sync_connector,
    upsert_normalized_job,
)
from app.services import job_connectors
from app.services.job_discovery_service import (
    freshness_label,
    passes_preference_filters,
    score_preference_match,
)
from conftest import TEST_USER


class FakeGreenhouseClient:
    @contextmanager
    def stream(self, method, url, params=None):
        if url.endswith("/jobs"):
            response = httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={
                    "jobs": [
                        {
                            "id": 42,
                            "title": "Senior Backend Engineer",
                            "updated_at": "2026-07-18T10:00:00Z",
                            "location": {"name": "Remote - US"},
                            "absolute_url": "https://boards.greenhouse.io/acme/jobs/42",
                            "content": "&lt;p&gt;Build Python APIs.&lt;/p&gt;",
                        }
                    ]
                },
            )
        else:
            response = httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={"name": "Acme"},
            )
        yield response


class FakeLeverClient:
    @contextmanager
    def stream(self, method, url, params=None):
        assert url == "https://api.eu.lever.co/v0/postings/acme"
        yield httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json=[
                {
                    "id": "lever-1",
                    "text": "Senior Backend Engineer",
                    "categories": {
                        "location": "Berlin, Germany",
                        "commitment": "Full-time",
                        "team": "Platform",
                        "department": "Engineering",
                        "level": "Senior",
                    },
                    "descriptionPlain": "Build Python services.",
                    "lists": [{"text": "Requirements", "content": "<li>FastAPI</li>"}],
                    "hostedUrl": "https://jobs.eu.lever.co/acme/lever-1",
                    "workplaceType": "hybrid",
                    "salaryRange": {
                        "currency": "EUR",
                        "interval": "year",
                        "min": 90000,
                        "max": 120000,
                    },
                }
            ],
        )


class FakeAshbyClient:
    @contextmanager
    def stream(self, method, url, params=None):
        assert url == "https://api.ashbyhq.com/posting-api/job-board/Acme"
        yield httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "apiVersion": "1",
                "jobs": [
                    {
                        "id": "ashby-1",
                        "title": "Product Engineer",
                        "location": "Remote - US",
                        "department": "Engineering",
                        "team": "Product",
                        "isListed": True,
                        "isRemote": True,
                        "workplaceType": "Remote",
                        "employmentType": "FullTime",
                        "descriptionPlain": "Build customer-facing software.",
                        "publishedAt": "2026-07-18T12:30:00Z",
                        "jobUrl": "https://jobs.ashbyhq.com/Acme/ashby-1",
                        "compensation": {
                            "summaryComponents": [
                                {
                                    "compensationType": "Salary",
                                    "interval": "1 YEAR",
                                    "currencyCode": "USD",
                                    "minValue": 130000,
                                    "maxValue": 160000,
                                }
                            ]
                        },
                    },
                    {
                        "id": "unlisted",
                        "title": "Confidential Role",
                        "isListed": False,
                        "jobUrl": "https://jobs.ashbyhq.com/Acme/unlisted",
                        "descriptionPlain": "Do not discover this role.",
                    },
                ],
            },
        )


class FakeSmartRecruitersClient:
    @contextmanager
    def stream(self, method, url, params=None):
        if url.endswith("/postings"):
            payload = {
                "offset": 0,
                "limit": 100,
                "totalFound": 1,
                "content": [
                    {
                        "id": "sr-1",
                        "name": "Data Engineer",
                        "releasedDate": "2026-07-17T09:00:00Z",
                        "visibility": "PUBLIC",
                        "company": {"identifier": "acme", "name": "Acme Inc."},
                        "location": {
                            "fullLocation": "Chicago, IL, USA",
                            "remote": False,
                            "hybrid": True,
                        },
                    }
                ],
            }
        else:
            assert url.endswith("/postings/sr-1")
            payload = {
                "id": "sr-1",
                "name": "Data Engineer",
                "active": True,
                "applyUrl": "https://jobs.smartrecruiters.com/acme/sr-1",
                "releasedDate": "2026-07-17T09:00:00Z",
                "company": {"identifier": "acme", "name": "Acme Inc."},
                "location": {
                    "fullLocation": "Chicago, IL, USA",
                    "remote": False,
                    "hybrid": True,
                },
                "industry": {"label": "Computer Software"},
                "department": {"label": "Data"},
                "function": {"label": "Engineering"},
                "typeOfEmployment": {"label": "Full-time"},
                "experienceLevel": {"label": "Mid-Senior Level"},
                "jobAd": {
                    "sections": {
                        "jobDescription": {
                            "title": "Job Description",
                            "text": "Build data platforms.",
                        },
                        "qualifications": {
                            "title": "Qualifications",
                            "text": "Python and SQL.",
                        },
                    }
                },
            }
        yield httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json=payload,
        )


class FakePersonioClient:
    @contextmanager
    def stream(self, method, url, params=None):
        assert url == "https://acme.jobs.personio.com/xml"
        yield httpx.Response(
            200,
            headers={"content-type": "text/xml"},
            content=b"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
                <workzag-jobs>
                  <position>
                    <id>personio-1</id>
                    <subcompany>Acme GmbH</subcompany>
                    <office>Munich</office>
                    <additionalOffices><office>Berlin</office></additionalOffices>
                    <department>Engineering</department>
                    <recruitingCategory>Software</recruitingCategory>
                    <name>Platform Engineer</name>
                    <jobDescriptions>
                      <jobDescription>
                        <name>The Role</name>
                        <value><![CDATA[<p>Build a hybrid cloud platform.</p>]]></value>
                      </jobDescription>
                    </jobDescriptions>
                    <employmentType>permanent</employmentType>
                    <schedule>full-time</schedule>
                    <seniority>experienced</seniority>
                    <createdAt>2026-07-01T10:00:00+00:00</createdAt>
                  </position>
                </workzag-jobs>""",
        )


class UnsafePersonioXMLClient:
    @contextmanager
    def stream(self, method, url, params=None):
        yield httpx.Response(
            200,
            headers={"content-type": "text/xml"},
            content=(
                b'<?xml version="1.0"?>'
                b'<!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
                b"<workzag-jobs><position><id>&xxe;</id></position></workzag-jobs>"
            ),
        )


def test_greenhouse_connector_normalizes_public_job_without_inventing_posted_date():
    jobs = GreenhouseConnector("acme", client=FakeGreenhouseClient()).fetch_jobs()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.external_job_id == "acme:42"
    assert job.company_name == "Acme"
    assert job.description == "Build Python APIs."
    assert job.workplace_type == "remote"
    assert job.seniority_level == "senior"
    assert job.source_posted_at is None
    assert job.source_updated_at == datetime(2026, 7, 18, 10, tzinfo=timezone.utc)


def test_greenhouse_connector_rejects_invalid_board_tokens():
    with pytest.raises(ConnectorError):
        GreenhouseConnector("../../internal")


def test_lever_connector_normalizes_eu_postings_without_guessing_dates():
    jobs = LeverConnector(
        "acme",
        company_name="Acme Inc.",
        region="eu",
        client=FakeLeverClient(),
    ).fetch_jobs()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.external_job_id == "eu:acme:lever-1"
    assert job.description == "Build Python services. Requirements FastAPI"
    assert job.workplace_type == "hybrid"
    assert job.employment_type == "full_time"
    assert job.seniority_level == "senior"
    assert (job.salary_min, job.salary_max, job.salary_currency) == (
        90000,
        120000,
        "EUR",
    )
    assert job.source_posted_at is None


def test_ashby_connector_excludes_unlisted_jobs_and_preserves_published_date():
    jobs = AshbyConnector(
        "Acme", company_name="Acme", client=FakeAshbyClient()
    ).fetch_jobs()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.external_job_id == "Acme:ashby-1"
    assert job.workplace_type == "remote"
    assert job.employment_type == "full_time"
    assert job.source_posted_at == datetime(2026, 7, 18, 12, 30, tzinfo=timezone.utc)
    assert (job.salary_min, job.salary_max, job.salary_currency) == (
        130000,
        160000,
        "USD",
    )


def test_smartrecruiters_connector_fetches_public_details_and_normalizes_metadata():
    jobs = SmartRecruitersConnector(
        "acme", client=FakeSmartRecruitersClient()
    ).fetch_jobs()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.company_name == "Acme Inc."
    assert (
        job.description
        == "Job Description Build data platforms. Qualifications Python and SQL."
    )
    assert job.location == "Chicago, IL, USA"
    assert job.workplace_type == "hybrid"
    assert job.employment_type == "full_time"
    assert job.seniority_level == "senior"
    assert job.industry == "Computer Software"
    assert job.source_posted_at == datetime(2026, 7, 17, 9, tzinfo=timezone.utc)


def test_personio_connector_parses_public_xml_without_treating_created_at_as_posted():
    jobs = PersonioConnector(
        "acme", company_name="Acme", client=FakePersonioClient()
    ).fetch_jobs()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.external_job_id == "com:acme:personio-1"
    assert job.canonical_url == (
        "https://acme.jobs.personio.com/job/personio-1?display=en"
    )
    assert job.location == "Munich, Berlin"
    assert job.description == "The Role Build a hybrid cloud platform."
    assert job.workplace_type == "hybrid"
    assert job.employment_type == "full_time"
    assert job.source_posted_at is None


def test_personio_rejects_xml_entities_and_unsafe_job_url_templates():
    with pytest.raises(ConnectorError, match="invalid XML"):
        PersonioConnector("acme", client=UnsafePersonioXMLClient()).fetch_jobs()
    with pytest.raises(ConnectorError, match="must be HTTPS"):
        PersonioConnector("acme", job_url_template="http://internal.example/jobs/{id}")


def test_connector_response_size_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(settings, "job_discovery_max_response_bytes", 4)
    with pytest.raises(ConnectorError, match="too large"):
        GreenhouseConnector("acme", client=FakeGreenhouseClient()).fetch_jobs()


def test_configured_connector_factory_honors_per_source_safety_flags(monkeypatch):
    monkeypatch.setattr(settings, "job_discovery_greenhouse_enabled", False)
    monkeypatch.setattr(settings, "job_discovery_lever_enabled", True)
    monkeypatch.setattr(
        settings,
        "job_discovery_lever_boards",
        [LeverBoardConfig(site="acme", company_name="Acme", region="eu")],
    )
    monkeypatch.setattr(settings, "job_discovery_ashby_enabled", True)
    monkeypatch.setattr(
        settings,
        "job_discovery_ashby_boards",
        [PublicATSBoardConfig(identifier="Acme", company_name="Acme")],
    )
    monkeypatch.setattr(settings, "job_discovery_smartrecruiters_enabled", True)
    monkeypatch.setattr(
        settings,
        "job_discovery_smartrecruiters_boards",
        [PublicATSBoardConfig(identifier="acme", company_name="Acme")],
    )
    monkeypatch.setattr(settings, "job_discovery_personio_enabled", True)
    monkeypatch.setattr(
        settings,
        "job_discovery_personio_boards",
        [PersonioBoardConfig(account="acme", company_name="Acme")],
    )

    connectors = configured_connectors()
    assert [(item.source_name, item.source_scope) for item in connectors] == [
        ("lever", "eu:acme"),
        ("ashby", "Acme"),
        ("smartrecruiters", "acme"),
        ("personio", "com:acme"),
    ]


def test_description_normalization_removes_scripts_and_decodes_html():
    assert description_text(
        "&lt;p&gt;Hello &amp;amp; welcome&lt;/p&gt;<script>x</script>"
    ) == ("Hello & welcome")


def test_preference_filtering_and_separate_preference_score():
    job = DiscoveredJob(
        company_name="Acme",
        company_normalized="acme",
        title="Backend Engineer",
        title_normalized="backend engineer",
        location="Chicago, IL",
        location_normalized="chicago, il",
        workplace_type="hybrid",
        employment_type="full_time",
        seniority_level="entry",
        description="Build Python and FastAPI services.",
        description_fingerprint="a" * 64,
        deduplication_key="b" * 64,
        keywords=[],
    )
    search = JobSearch(
        user_id=TEST_USER.id,
        name="Backend",
        target_titles=["Backend Engineer"],
        adjacent_titles=[],
        seniority_levels=["entry"],
        employment_types=["full time"],
        locations=["Chicago"],
        workplace_types=["hybrid"],
        industries=[],
        required_keywords=["Python"],
        excluded_keywords=[],
        excluded_companies=[],
        recency="7d",
        notification_frequency="off",
    )

    assert passes_preference_filters(job, search)
    score, reasons = score_preference_match(job, search)
    assert score == 1.0
    assert any("Title" in reason for reason in reasons)

    search.excluded_companies = ["Acme"]
    assert not passes_preference_filters(job, search)


def test_freshness_label_does_not_guess_missing_dates():
    now = datetime(2026, 7, 19, 12, tzinfo=timezone.utc)
    assert freshness_label(None, now=now) == "Date unavailable"
    assert freshness_label(now - timedelta(hours=2), now=now) == "Posted today"


@pytest.fixture
def discovery_client():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db.execute(text("DELETE FROM users"))
            db.execute(text("DELETE FROM job_source_postings"))
            db.execute(text("DELETE FROM discovered_jobs"))
            db.add(
                User(
                    id=TEST_USER.id,
                    external_subject=TEST_USER.external_subject,
                    email=TEST_USER.email,
                    name=TEST_USER.name,
                )
            )
            db.commit()
    except OperationalError:
        pytest.skip("PostgreSQL integration database is unavailable")

    try:
        yield TestClient(app)
    finally:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM users"))
            db.execute(text("DELETE FROM job_source_postings"))
            db.execute(text("DELETE FROM discovered_jobs"))
            db.commit()


def _catalog_job(db, *, title: str, posted_at):
    job = DiscoveredJob(
        id=uuid4(),
        company_name="Acme",
        company_normalized="acme",
        title=title,
        title_normalized=title.casefold(),
        location="Chicago, IL",
        location_normalized="chicago, il",
        workplace_type="hybrid",
        employment_type="full_time",
        seniority_level="entry",
        description="Build Python APIs with FastAPI.",
        description_fingerprint=uuid4().hex + uuid4().hex,
        deduplication_key=uuid4().hex + uuid4().hex,
        keywords=["Python", "FastAPI"],
        source_posted_at=posted_at,
        verification_status="active",
    )
    db.add(job)
    db.flush()
    db.add(
        JobSourcePosting(
            discovered_job_id=job.id,
            source_name="greenhouse",
            external_job_id=f"acme:{job.id}",
            canonical_url=f"https://boards.greenhouse.io/acme/jobs/{job.id}",
            source_posted_at=posted_at,
            verification_status="active",
        )
    )
    return job


def test_saved_search_recency_actions_and_conversion(discovery_client):
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        recent = _catalog_job(
            db, title="Backend Engineer", posted_at=now - timedelta(days=2)
        )
        old = _catalog_job(
            db, title="Backend Engineer II", posted_at=now - timedelta(days=20)
        )
        unknown = _catalog_job(db, title="Backend Engineer III", posted_at=None)
        recent_id, old_id, unknown_id = recent.id, old.id, unknown.id
        db.commit()

    status = discovery_client.get("/job-discovery/status")
    assert status.status_code == 200, status.text
    assert status.json()["active_job_count"] >= 3
    assert status.json()["active_source_count"] >= 3
    assert status.json()["last_verified_at"] is not None

    created = discovery_client.post(
        "/job-discovery/searches",
        json={
            "name": "Chicago backend",
            "target_titles": ["Backend Engineer"],
            "locations": ["Chicago"],
            "required_keywords": ["Python"],
            "recency": "7d",
        },
    )
    assert created.status_code == 200, created.text
    search_id = created.json()["id"]
    invalid_update = discovery_client.patch(
        f"/job-discovery/searches/{search_id}",
        json={"salary_min": 100, "salary_max": 50},
    )
    assert invalid_update.status_code == 422

    finite_feed = discovery_client.get(
        "/job-discovery/feed",
        params={"search_id": search_id, "sort": "newest"},
    )
    assert finite_feed.status_code == 200, finite_feed.text
    assert [item["id"] for item in finite_feed.json()["items"]] == [str(recent_id)]

    all_feed = discovery_client.get(
        "/job-discovery/feed",
        params={"search_id": search_id, "recency": "all", "sort": "newest"},
    )
    assert all_feed.status_code == 200, all_feed.text
    assert [item["id"] for item in all_feed.json()["items"]] == [
        str(recent_id),
        str(old_id),
        str(unknown_id),
    ]
    assert all_feed.json()["items"][-1]["freshness_label"] == "Date unavailable"

    dismissed = discovery_client.put(
        f"/job-discovery/jobs/{recent_id}/action", json={"state": "dismissed"}
    )
    assert dismissed.status_code == 200, dismissed.text
    assert discovery_client.get(
        "/job-discovery/feed", params={"search_id": search_id, "recency": "all"}
    ).json()["items"][0]["id"] != str(recent_id)

    cleared = discovery_client.delete(f"/job-discovery/jobs/{recent_id}/action")
    assert cleared.status_code == 200
    converted = discovery_client.post(
        f"/job-discovery/jobs/{recent_id}/convert", json={"search_id": search_id}
    )
    assert converted.status_code == 200, converted.text
    application_id = converted.json()["application_id"]
    application = discovery_client.get(f"/applications/{application_id}")
    assert application.status_code == 200
    assert application.json()["job_url"].startswith("https://boards.greenhouse.io/")
    cannot_overwrite_conversion = discovery_client.put(
        f"/job-discovery/jobs/{recent_id}/action", json={"state": "dismissed"}
    )
    assert cannot_overwrite_conversion.status_code == 409


class StubConnector:
    source_name = "greenhouse"

    def __init__(self, source_scope: str, jobs: list[NormalizedJob]):
        self.source_scope = source_scope
        self.jobs = jobs

    def fetch_jobs(self):
        return self.jobs


def _normalized_job(scope: str) -> NormalizedJob:
    return NormalizedJob(
        source_name="greenhouse",
        external_job_id=f"{scope}:42",
        canonical_url=f"https://boards.greenhouse.io/{scope}/jobs/42",
        company_name="Acme",
        title="Backend Engineer",
        location="Chicago, IL",
        description="Build Python APIs.",
        raw_payload={"id": 42},
    )


def test_sync_scopes_removals_to_one_board_and_retains_cross_source_provenance(
    discovery_client, monkeypatch
):
    monkeypatch.setattr(job_connectors, "validate_public_job_url", lambda url: url)
    with SessionLocal() as db:
        first = sync_connector(
            db, StubConnector("acme_one", [_normalized_job("acme_one")])
        )
        second = sync_connector(
            db, StubConnector("acmeXone", [_normalized_job("acmeXone")])
        )
        assert first == {"seen": 1, "created": 1, "removed": 0}
        assert second == {"seen": 1, "created": 1, "removed": 0}
        assert db.query(DiscoveredJob).count() == 1
        assert db.query(JobSourcePosting).count() == 2

        acme_removed = sync_connector(db, StubConnector("acme_one", []))
        assert acme_removed["removed"] == 1
        discovered = db.query(DiscoveredJob).one()
        assert discovered.verification_status == "active"

        other_removed = sync_connector(db, StubConnector("acmeXone", []))
        assert other_removed["removed"] == 1
        db.refresh(discovered)
        assert discovered.verification_status == "removed"


def test_every_public_ats_connector_flows_through_normalized_ingestion(
    discovery_client, monkeypatch
):
    monkeypatch.setattr(job_connectors, "validate_public_job_url", lambda url: url)
    connectors = (
        LeverConnector(
            "acme", company_name="Acme", region="eu", client=FakeLeverClient()
        ),
        AshbyConnector("Acme", company_name="Acme", client=FakeAshbyClient()),
        SmartRecruitersConnector("acme", client=FakeSmartRecruitersClient()),
        PersonioConnector("acme", company_name="Acme", client=FakePersonioClient()),
    )
    with SessionLocal() as db:
        for connector in connectors:
            result = sync_connector(db, connector)
            assert result == {"seen": 1, "created": 1, "removed": 0}
        assert {source.source_name for source in db.query(JobSourcePosting).all()} == {
            "lever",
            "ashby",
            "smartrecruiters",
            "personio",
        }


def test_canonical_url_and_normalized_company_identity_deduplicate_sources(
    discovery_client, monkeypatch
):
    monkeypatch.setattr(job_connectors, "validate_public_job_url", lambda url: url)
    canonical_url = "https://jobs.example.com/role-1"
    first = NormalizedJob(
        source_name="lever",
        external_job_id="global:acme:1",
        canonical_url=canonical_url,
        company_name="Acme Inc.",
        title="Backend Engineer",
        location="Chicago",
        description="Build Python APIs.",
    )
    second = NormalizedJob(
        source_name="ashby",
        external_job_id="acme:2",
        canonical_url=canonical_url,
        company_name="Acme GmbH",
        title="Backend Engineer",
        location="Chicago",
        description="Updated copy for the same role.",
    )
    with SessionLocal() as db:
        first_job, _, _ = upsert_normalized_job(db, first)
        second_job, _, _ = upsert_normalized_job(db, second)
        db.commit()
        assert first_job.id == second_job.id
        assert db.query(DiscoveredJob).count() == 1
        assert db.query(JobSourcePosting).count() == 2
