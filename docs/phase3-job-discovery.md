# Phase 3 job discovery foundation

Last updated: 2026-07-19

## Current scope

This Phase 3 slice adds the backend foundation and an authenticated discovery
workspace without changing or removing manual application creation and URL parsing.

Implemented:

- Private saved searches with target and adjacent titles, seniority, employment
  type, locations, workplace preference, salary range, industries, required and
  excluded keywords/companies, resume selection, recency, and notification
  frequency.
- A shared normalized job catalog with separate source-provenance rows.
- `recommended`, `newest`, and `most_relevant` feed ordering.
- Explicit `24h`, `7d`, `14d`, `30d`, and `all` recency modes. Finite modes
  exclude postings without a trustworthy source posting date.
- Separate preference-match and resume-match scores with concise reason codes.
- Save, dismiss, mark-duplicate, clear-action, and convert-to-application APIs.
- A normalized connector protocol with public Greenhouse, Lever (global and EU),
  Ashby, SmartRecruiters, and Personio employer-board implementations.
- Active-posting rechecks, removal handling, exact normalized deduplication, a
  seven-day raw-payload retention window, and a default-off startup safety flag.
- A `/discover` frontend for saved-search creation/editing, recency and sort
  controls, match signals and reasons, source links, job actions, company hiding,
  and conversion into the existing application workflow.
- Authenticated catalog health showing active normalized jobs, active provenance
  rows, and the most recent source verification time.

Not yet implemented:

- Scheduled background execution, connector retries/backoff, health metrics, and
  per-source rate-budget enforcement.
- Broader fuzzy cross-source deduplication and measured relevance evaluation.
- Notifications or digests.

The operator must leave each connector disabled in production until scheduling,
monitoring, board-level source review, and a UI rollout are ready.

## Data boundaries

`discovered_jobs` is a shared source-independent catalog. It stores normalized job
content, an exact deduplication key, the earliest trustworthy source posting time,
and active/removed status.

`job_source_postings` retains source name, external ID, canonical URL, source
timestamps, first/last seen times, verification state, and short-lived raw source
payloads. Raw payloads expire after seven days and are purged by subsequent syncs.

`job_searches` and `job_discovery_actions` are user-owned. Both use application
ownership predicates and PostgreSQL row-level security. Search-to-resume and
action-to-application relationships use owner-matching foreign keys.

Recency is only a query-time search preference. Old but active jobs remain in the
catalog. A missing or ambiguous posting timestamp remains null, appears as
`Date unavailable` in the all-active feed, is excluded from finite recency windows,
and sorts below dated jobs in the newest view.

## API

All endpoints require the existing authenticated API session.

- `GET /job-discovery/searches`
- `POST /job-discovery/searches`
- `GET /job-discovery/status`
- `GET /job-discovery/searches/{search_id}`
- `PATCH /job-discovery/searches/{search_id}`
- `DELETE /job-discovery/searches/{search_id}`
- `GET /job-discovery/feed?search_id=...&recency=7d&sort=recommended`
- `PUT /job-discovery/jobs/{job_id}/action`
- `DELETE /job-discovery/jobs/{job_id}/action`
- `POST /job-discovery/jobs/{job_id}/convert`

Converting is idempotent for an already converted user/job pair and preserves the
canonical source URL and normalized description in the existing application.

## Connector acquisition policy

All connectors make read-only requests to documented public employer-job feeds.
They never submit applications, request ATS credentials, use browser sessions, or
automate authenticated pages. Every source has an independent default-off startup
flag. All requests use fixed HTTPS API/feed origins, reject redirects, set a
RolePilot service user agent, enforce timeout/content-type/response-size limits,
and abort a sync rather than expiring jobs when a source response is malformed or
truncated. Canonical job URLs are separately checked by the existing public-network
SSRF validator before persistence.

### Greenhouse

Acquisition method:

- Only Greenhouse's documented, unauthenticated Job Board API GET endpoints are
  used: board metadata and `GET /v1/boards/{board_token}/jobs?content=true`.
- RolePilot does not use the authenticated application-submission endpoint, HTML
  scraping, browser sessions, cookies, passwords, or anti-bot bypasses.
- Requests go only to the fixed `https://boards-api.greenhouse.io` API origin, do
  not follow redirects, identify RolePilot with a service user agent, use the
  configured timeout, require JSON, and stream through the response-size cap.
- Canonical job URLs returned by the source are separately validated with the
  existing public-network SSRF checks before persistence.

Source-date handling:

- Greenhouse's public list response documents `updated_at`, not a guaranteed
  original publication time. It is stored as `source_updated_at`; RolePilot does
  not relabel it as a posting date.

Attribution and retention:

- Every feed item exposes its Greenhouse source and canonical employer URL.
- The normalized job remains while active or needed for user history. Raw API
  payloads have a seven-day retention window.
- Greenhouse does not publish a numeric rate limit for this public endpoint in the
  Job Board API documentation. The current operator script is sequential and
  bounded to explicitly configured boards. Production scheduling must add a
  conservative rate budget and observable health before enabling the connector.

Because this uses the documented API rather than crawling employer HTML pages,
robots rules do not control the API request path. Any future HTML connector must
document and enforce robots behavior separately before activation.

Official reference: [Greenhouse Job Board API](https://developers.greenhouse.io/job-board.html)

### Lever

- Uses only `GET /v0/postings/{site}` with JSON mode on Lever's documented global
  or EU Postings API origin.
- Lever states that published postings are publicly viewable and may be collected
  by third parties. Internal and non-published jobs are not exposed by this API.
- Pagination is bounded by the configured per-board job ceiling. The connector
  stores hosted job URLs, workplace type, commitment, team/department, level, and
  salary ranges when present.
- Lever does not expose a publication timestamp in the documented JSON posting
  object, so these jobs correctly remain `Date unavailable`.
- The documented numeric warning concerns application-creation POSTs, which
  RolePilot never calls. No numeric GET limit is published; sync remains sequential
  and operator-controlled.

Official reference: [Lever Postings API](https://github.com/lever/postings-api)

### Ashby

- Uses only Ashby's documented public
  `GET /posting-api/job-board/{board}` endpoint with compensation enabled.
- Only records with `isListed=true` are ingested. Direct-link/unlisted postings are
  deliberately excluded from discovery.
- `publishedAt` is stored as the source posting time because Ashby documents it as
  when the posting was last published. Workplace, employment, department/team,
  secondary metadata, and annual salary components are normalized when present.
- The endpoint is not paginated; RolePilot rejects a board above its configured
  job ceiling instead of ingesting a partial list and falsely expiring jobs.
- Ashby publishes no numeric limit for this public endpoint; sync remains
  sequential and operator-controlled.

Official reference: [Ashby Job Postings API](https://developers.ashbyhq.com/docs/public-job-posting-api)

### SmartRecruiters

- Uses only the company-scoped public Posting API list and detail GET endpoints.
  No `X-SmartToken`, customer API key, OAuth token, or publication-feed credential
  is requested or stored.
- Only public, active postings are normalized. `releasedDate` is retained as the
  source posting timestamp; location/workplace, employment type, experience level,
  industry, department/function, and public job-ad sections are retained.
- Listing pagination and detail requests are sequential and bounded by the same
  per-board ceiling. A count mismatch or incomplete page aborts the sync.
- The public Posting documentation provides executable unauthenticated examples
  but no numeric GET rate limit, so production scheduling must remain conservative.

Official references: [SmartRecruiters public Posting endpoints](https://developers.smartrecruiters.com/docs/endpoints), [unauthenticated public endpoint overview](https://developers.smartrecruiters.com/docs/customer-overview)

### Personio

- Uses Personio's documented, credential-free employer XML feed at
  `{account}.jobs.personio.{com|de}/xml?language=en`.
- The feed contains only jobs the employer published to its career page/XML feed.
  RolePilot parses it with an entity-safe XML parser and never calls the Recruiting
  API or sends candidate data.
- Personio's `createdAt` value is not documented as the publication time, so it is
  retained only in short-lived raw provenance and is not shown as a posting date.
- The standard hosted job URL is used by default. Operators whose Personio board
  redirects to a corporate careers site may provide an HTTPS per-job template that
  must contain `{id}`.
- Personio recommends syncing the XML connection at least hourly for integrity;
  RolePilot does not exceed that cadence by itself and currently runs only when an
  operator invokes the bounded sync command.

Official references: [Personio XML integration](https://support.personio.de/hc/en-us/articles/207576365-Integrate-jobs-from-Personio-into-your-company-website-via-XML), [Personio XML FAQ](https://support.personio.de/hc/en-us/articles/29375445597725-Frequently-asked-questions-on-XML-job-integration)

## Configuration and operation

The production startup safety flag is off by default:

```env
JOB_DISCOVERY_GREENHOUSE_ENABLED=false
JOB_DISCOVERY_GREENHOUSE_BOARDS=[]
JOB_DISCOVERY_LEVER_ENABLED=false
JOB_DISCOVERY_LEVER_BOARDS=[]
JOB_DISCOVERY_ASHBY_ENABLED=false
JOB_DISCOVERY_ASHBY_BOARDS=[]
JOB_DISCOVERY_SMARTRECRUITERS_ENABLED=false
JOB_DISCOVERY_SMARTRECRUITERS_BOARDS=[]
JOB_DISCOVERY_PERSONIO_ENABLED=false
JOB_DISCOVERY_PERSONIO_BOARDS=[]
JOB_DISCOVERY_MAX_RESPONSE_BYTES=8388608
JOB_DISCOVERY_MAX_JOBS_PER_BOARD=500
```

Greenhouse uses a JSON list of board tokens. The other connectors use explicit
objects so company aliases and Lever region can be normalized consistently:

```env
JOB_DISCOVERY_GREENHOUSE_BOARDS='["example"]'
JOB_DISCOVERY_LEVER_BOARDS='[{"site":"example","company_name":"Example Inc.","region":"global"}]'
JOB_DISCOVERY_ASHBY_BOARDS='[{"identifier":"Example","company_name":"Example Inc."}]'
JOB_DISCOVERY_SMARTRECRUITERS_BOARDS='[{"identifier":"example","company_name":"Example Inc."}]'
JOB_DISCOVERY_PERSONIO_BOARDS='[{"account":"example","company_name":"Example GmbH","domain":"com"}]'
```

After applying the `0006_job_discovery` migration, an operator can run one bounded
sync from the backend directory:

```bash
python scripts/sync_job_sources.py
```

The feeds above are public employer ATS feeds. They do not require a user account,
job-board password, OAuth token, or vendor API key. The operator only supplies the
public board/account identifiers in environment configuration. Run the command on
a conservative schedule (for example, a Render Cron Job) using the same backend
image and environment; the script returns a non-zero exit code when any configured
connector fails so the scheduler can alert.

Each connector is scoped by source plus board/account (and Lever region). Each sync
upserts current jobs, records first/last seen times, marks source posts missing from
that exact board as removed, stops recommending jobs with no active source, and
clears expired raw payloads. One connector failure is rolled back and reported
without preventing later configured connectors from running.

Changing the flag currently requires a service restart. A runtime control-plane
kill switch that can disable a connector without a restart or deploy remains open.

## Verification

The Phase 3 tests cover Greenhouse, Lever global/EU, Ashby listed/unlisted behavior,
SmartRecruiters list/detail ingestion, Personio XML parsing, source-specific date
semantics, response ceilings, configuration flags, scoped removals, canonical and
cross-source deduplication, preference scoring, saved-search recency, actions,
conversion, cross-user isolation, RLS, and account deletion cleanup.

Live read-only contract checks on 2026-07-19 successfully normalized current
public boards from Lever, Ashby, SmartRecruiters, and Personio in addition to the
fixture-based automated coverage.

An end-to-end live catalog check then ingested 274 Lever postings, 62 Ashby
postings, 9 SmartRecruiters postings, and 1 Personio posting into an isolated
PostgreSQL database. A repeated sync produced zero duplicate source rows and zero
false removals for all four connectors.

The verified migration path is fresh upgrade, metadata consistency check,
downgrade to `0005_source_evidence`, and re-upgrade to head on PostgreSQL 16 with
pgvector.
