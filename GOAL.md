# RolePilot Product and Engineering Goals

Last updated: 2026-07-18

## Product goal

RolePilot should become a private, trustworthy career workspace where each user can:

1. Upload and analyze one or more resumes.
2. Save a job posting and understand its requirements.
3. See an evidence-based resume-to-job match.
4. Generate, review, edit, and export a tailored resume without fabricated claims.
5. Manage applications, resumes, and supporting evidence without another user being able to access them.

The product should optimize for trust and usefulness, not just generation volume. A tailored resume is successful only when it is relevant to the job, grounded in the user's real experience, editable, and identical to what is exported.

## Current system snapshot

The repository already contains a functional end-to-end prototype:

- A Next.js frontend for application tracking, resume upload and analysis, job parsing, resume matching, tailored bullets, full-draft preview, and export.
- A FastAPI backend with SQLAlchemy models for applications, resumes, matches, tailored content, full drafts, project evidence, and evidence chunks.
- PostgreSQL and pgvector retrieval using `text-embedding-3-small`.
- Hybrid retrieval that combines vector similarity and keyword overlap with reciprocal-rank fusion.
- OpenAI-powered job parsing, resume feedback, matching, tailoring, and full-draft generation.
- DOCX and PDF export.
- A retrieval evaluation script with keyword, semantic, and hybrid metrics, plus labeled evaluation data.
- CI configuration for frontend lint/type/build and backend tests.

This is a strong prototype foundation, but it is still effectively a single-user application. Authentication, ownership, data isolation, generation grounding, test coverage, and operational controls must be addressed before treating it as a multi-user product.

## Highest-priority findings

### 1. There is no user or tenant boundary

Every route is public and every database query is global. `GET /resume/latest` returns the latest resume in the entire database, application IDs can be read or changed directly, and retrieval searches every project evidence chunk. Adding a login page without changing these queries would not protect user data.

### 2. Generated content can include user-specific hard-coded skills

The full-resume builder currently appends a fixed skill inventory to every generated resume. This can leak one person's background into another person's draft and can fabricate skills even in single-user use. This should be removed before onboarding additional users.

### 3. Retrieval is real, but not yet safely grounded

The hybrid retriever is a good baseline, but it uses a fixed top-k, a noisy full-job query, equal rank fusion, no reranker, no diversity control, no vector index definition, and no tenant filter. The generation response contains free-form evidence names rather than verifiable evidence IDs, so citations cannot currently be audited.

### 4. The generated preview and exported file can differ

The frontend saves a full draft, but export endpoints call the model again instead of exporting that saved draft. A download can therefore differ from the approved preview, incur extra cost, or introduce new unsupported claims.

### 5. Production safety and reliability are limited

Database tables are created with `Base.metadata.create_all` instead of versioned migrations. Job URL parsing can request arbitrary URLs and needs SSRF protection. Upload size/page limits, rate limits, AI timeouts/retries, structured logging, cost tracking, background jobs, and cleanup policies are absent. Backend coverage currently exercises only health/root and one not-found case.

## Guiding principles

- Privacy by default: ownership is enforced in the backend, never trusted to the client.
- Grounded generation: every material generated claim must be traceable to resume or evidence content.
- User control: AI output is a draft that can be edited, accepted, rejected, and regenerated selectively.
- Deterministic export: exported content must match the saved, user-approved draft.
- Measured RAG: retrieval changes ship only after evaluation against a labeled baseline.
- Incremental delivery: preserve the working application flow while replacing risky foundations in stages.

## Roadmap

### Phase 0 — Remove cross-user and fabrication risks

Goal: make the current prototype safe enough to evolve.

- [x] Remove the fixed personal skill lists from `build_full_tailored_resume_draft`; only use skills supported by the selected resume or saved evidence.
- [x] Export the saved full-resume draft rather than regenerating it during DOCX/PDF download.
- [x] Change matching and generation endpoints to accept resource IDs, then load the resume and application server-side. Do not accept authoritative resume text from the browser.
- [x] Add upload size, page count, extracted-text length, and supported-file validation.
- [x] Add SSRF defenses to job URL parsing: allow only HTTP/HTTPS, resolve and reject private/loopback/link-local addresses, cap redirects and response size, and reject non-text content.
- [x] Stop returning raw internal exception messages to clients; log a request ID and return a safe error response.
- [x] Replace permissive string fields such as application status with validated enums and constraints.
- [x] Add Alembic configuration and an initial migration; remove table creation as an application-startup side effect.

Acceptance criteria:

- A generated draft contains no skill or claim absent from that user's source data.
- Exporting a saved draft twice produces the same content and does not call the model.
- Unsafe job URLs and oversized uploads are rejected before external processing.
- Schema changes can be applied and rolled back through versioned migrations.

Phase 0 verification completed on 2026-07-18:

- Backend tests cover server-owned AI inputs, saved-draft export, generated skill and numeric-claim grounding, PDF limits, SSRF cases, safe errors, migration bootstrapping, and status validation.
- Alembic upgrade, metadata consistency, full rollback, fresh re-upgrade, and guarded legacy-schema bootstrap were exercised against PostgreSQL 16 with pgvector.
- Frontend lint, TypeScript validation, and the Next.js production build pass with the updated API contract.
- Next.js was patched from 16.2.1 to 16.2.10, eliminating the high-severity production advisories reported by `npm audit` at the time of verification.

### Phase 1 — Per-user authentication and data isolation

Goal: every user has a private workspace with server-enforced ownership.

#### Identity design

- [x] Choose an OpenID Connect-compatible authentication provider and document the decision. Auth0 with a token-mediating Next.js frontend is recorded in `docs/adr/0001-authentication-and-session-boundary.md`.
- [x] Add frontend sign-up, sign-in, sign-out, session refresh, protected routes, and an account menu.
- [x] Validate access tokens in FastAPI using issuer, audience, signature, and expiry—not a shared user ID supplied by the frontend.
- [x] Add a `users` table keyed by an internal UUID with a unique external identity subject, email, name, timestamps, and optional onboarding state.
- [x] Replace the unused default `jwt_secret="change-me"` configuration with required, environment-specific auth settings.

#### Ownership model

- [x] Add non-null `user_id` ownership to applications, resumes, project evidence, and generated artifacts, or enforce ownership transitively where appropriate.
- [x] Add ownership-aware foreign keys, indexes, and uniqueness rules. Existing one-draft-per-application constraints are protected by owner-matching composite foreign keys.
- [x] Introduce a `get_current_user` dependency and repository/service helpers that always include the current user in reads and writes.
- [x] Scope application CRUD, latest/selected resume, match, tailored draft, full draft, evidence retrieval, and export queries to the authenticated user.
- [x] Ensure related resource IDs belong to the same user before matching, tailoring, saving, or exporting.
- [x] Add PostgreSQL row-level security as defense in depth after application-level scoping is proven.
- [x] Define a one-time migration policy for existing global data: quarantine it under a disabled legacy principal and require an explicit, guarded transfer to a verified OIDC subject.
- [x] Remove personal seed/evaluation data from distributable builds and document retention/deletion behavior for resumes and exports.

#### Authentication tests

- [x] Test unauthenticated access to every protected endpoint.
- [x] Test that User A cannot read, update, delete, match, retrieve against, or export User B's resources, including guessed IDs.
- [x] Test expired, malformed, wrong-issuer, and wrong-audience tokens.
- [x] Test account deletion and cascading cleanup.

Acceptance criteria:

- No protected endpoint succeeds without a valid session.
- Cross-user resource tests return a non-disclosing 404 or 403 and never access another user's row.
- Retrieval SQL includes an ownership predicate before vector ranking.
- Each user sees only their own applications, resumes, evidence, drafts, and exports.

Phase 1 verification completed on 2026-07-18:

- Auth0 uses encrypted HTTP-only Next.js sessions and a token-mediating `/api/backend/*` route; browser JavaScript does not receive API access tokens.
- FastAPI accepts only RS256 access tokens with the configured issuer and audience and maps the immutable OIDC subject to an internal UUID.
- PostgreSQL/pgvector integration tests cover guessed cross-user IDs, relationship ownership, vector retrieval filtering before ranking, saved drafts/exports, RLS presence, and account-deletion cascades.
- Alembic upgrade, downgrade, metadata consistency, legacy quarantine, and the guarded legacy-owner transfer were exercised against PostgreSQL 16 with pgvector.
- The personal seed corpus, derived evaluation exports, and embedding cache were removed; local private artifacts are ignored and retention/deletion behavior is documented.

### Phase 2 — Resume and evidence data foundation

Goal: give generation a clean, structured, user-managed source of truth.

- [x] Support multiple resumes with labels, an explicit default resume, archive/delete, and resume selection per application. Replace the global "latest resume" behavior.
- [x] Store the original upload in private object storage with encryption and signed, short-lived access; keep only required derived text in PostgreSQL.
- [x] Parse resumes into structured sections and stable source items: contact, education, experience, projects, skills, and individual bullets.
- [x] Add a source fingerprint and version so analysis, chunks, matches, and drafts can be marked stale when a resume changes.
- [x] Build project-evidence management in the frontend; the backend currently supports only create and list. Add edit, delete, re-embed, and ingestion-status endpoints.
- [x] Let users convert resume bullets into evidence entries and add outcomes, metrics, dates, skills, and links through a guided form.
- [x] Separate user assertions from AI suggestions. Metrics suggested by the model should remain unverified until the user confirms them.
- [x] Use transactions or an asynchronous ingestion job so an evidence row cannot appear ready when its chunk embedding failed.

Acceptance criteria:

- A user can choose which resume is matched and tailored for each application.
- Every generated bullet points to stable source item IDs and source versions.
- Editing a source marks dependent retrieval data and generated artifacts stale.
- Evidence ingestion exposes `pending`, `ready`, and `failed` states with a retry action.

Phase 2 verification completed on 2026-07-18:

- PostgreSQL/pgvector integration tests cover explicit default and per-application resume selection, archive reassignment, cross-user guards, stable source UUIDs across edits/insertion, artifact staleness, citation ownership/version checks, metric confirmation, and failed/retry evidence ingestion.
- Private object-storage tests cover opaque per-user keys, server-side encryption, five-minute signed reads, and deletion; production deployment is configured to fail closed with `OBJECT_STORAGE_REQUIRED=true` when its private bucket is unavailable.
- Alembic revisions `0004` and `0005` passed fresh upgrade, metadata consistency, full rollback, and re-upgrade against PostgreSQL 16 with pgvector.
- The backend suite passes 54 tests; frontend lint, TypeScript validation, and the Next.js production build pass with the new resume library, parsed editor, evidence library, source citations, and stale-state UI.
- Render object-storage variables and the private bucket remain a deployment operation documented in `docs/phase2-data-foundation.md`; no storage secret belongs in Vercel.

### Phase 3 — Better retrieval and RAG

Goal: retrieve the smallest, most relevant set of user evidence and make its use visible and testable.

#### Retrieval quality

- [ ] Replace summary-plus-bullet-only chunking with content-aware chunks for resume bullets, project bullets, skills, outcomes, responsibilities, and verified metrics.
- [ ] Store retrieval metadata with every chunk: `user_id`, source type, source ID, source version, section, title, dates, skills, embedding model, and content hash.
- [ ] Build a focused query from weighted job fields instead of embedding the entire raw posting equally. Prioritize role title, required skills, responsibilities, preferred skills, and domain terms.
- [ ] Add PostgreSQL full-text search/BM25-style lexical ranking for exact technologies, acronyms, and certifications; combine it with vector search.
- [ ] Add an HNSW or IVFFlat pgvector index and the supporting tenant/filter indexes. Verify plans with realistic user data volume.
- [ ] Retrieve a wider candidate set, deduplicate near-identical chunks, enforce source diversity, then rerank candidates against the role requirements.
- [ ] Tune candidate count, final top-k, rank-fusion weights, and similarity thresholds from evaluation data rather than hard-coding them globally.
- [ ] Batch and cache embeddings by content hash; record the embedding model/version and provide a controlled re-index path.
- [ ] Return retrieval scores and reason codes for observability, while treating score magnitudes as diagnostic rather than user-facing truth.

#### Grounding and citations

- [ ] Pass stable evidence IDs and verbatim source spans into generation.
- [ ] Require every tailored bullet to return cited evidence IDs, not free-form source names.
- [ ] Validate that cited IDs were actually retrieved and belong to the current user.
- [ ] Add a post-generation grounding check for unsupported tools, skills, dates, employers, education, metrics, and outcomes.
- [ ] Block unsupported claims from export and ask the user to confirm or remove ambiguous claims.
- [ ] Show citations in the UI with a "why this was used" view and the original source text.

#### Evaluation

- [ ] Preserve the existing keyword/semantic/hybrid evaluation harness as the baseline.
- [ ] Expand beyond the current small, personal corpus to de-identified examples across software, hardware, data, product, research, and non-technical roles.
- [ ] Split evaluation data into tuning and held-out regression sets.
- [ ] Track Recall@k, nDCG@k, MRR, source diversity, zero-result rate, latency, and embedding/reranking cost.
- [ ] Add generation evaluations for citation validity, unsupported-claim rate, job relevance, edit distance after user review, and export consistency.
- [ ] Run retrieval regression tests in CI without making live model calls; run scheduled online evaluation separately when credentials are available.

Initial release targets:

- Recall@5 of at least 0.90 on the held-out retrieval set.
- nDCG@5 measurably higher than the current hybrid baseline.
- 100% of generated bullets contain valid in-scope citations.
- 0 unsupported numeric claims in the grounding test set.
- P95 retrieval latency under 500 ms excluding initial evidence ingestion.

### Phase 4 — Better tailoring and match quality

Goal: make feedback specific, reproducible, and useful without overstating fit.

- [ ] Use structured outputs with explicit schemas for matching, tailoring, and full-draft generation, as already done for resume analysis and job parsing.
- [ ] Produce a structured match score with category-level evidence: required skills, preferred skills, relevant experience, domain alignment, and missing qualifications.
- [ ] Do not infer a fit label by searching prose for phrases such as "strong fit". Calculate display labels from the structured result and show the evidence behind them.
- [ ] Distinguish "not found in provided evidence" from "candidate does not have this skill."
- [ ] Generate a change plan before rewriting: keep, edit, reorder, or omit each source bullet.
- [ ] Support section-level and bullet-level regeneration with user instructions while preserving locked content.
- [ ] Store prompt version, model, source versions, retrieved chunk IDs, latency, token usage, and generation status with each artifact.
- [ ] Add draft history instead of overwriting the only match/tailored/full-draft row. Let users compare and restore versions.
- [ ] Add model timeouts, bounded retries with backoff, idempotency keys, and clear partial-failure behavior.
- [ ] Move long-running analysis, embedding, generation, and PDF conversion to background jobs with progress states.

Acceptance criteria:

- The same saved artifact can be inspected later with its exact sources and generation metadata.
- Users can regenerate one bullet without replacing accepted content elsewhere.
- Match labels are deterministic from structured values and do not depend on prose wording.
- Failed AI requests can be retried safely without duplicate records.

### Phase 5 — Better UI and product workflow

Goal: make the product feel like one guided workflow rather than several large output cards.

#### Information architecture

- [ ] Create a shared authenticated application shell instead of repeating the top navigation on every page.
- [ ] Add a first-run checklist: upload resume, review parsed sections, add/confirm evidence, save a job, run match, tailor, review, export.
- [ ] Add dedicated navigation for Dashboard, Applications, Resumes, Evidence Library, and Account.
- [ ] Redesign the application detail screen as a clear sequence: Job -> Match -> Tailor -> Review -> Export, with prerequisite and stale-state indicators.
- [ ] Keep the job context available in a compact side panel while reviewing match results and edits.

#### Application dashboard

- [ ] Add search, filters, sorting, pagination, saved views, and status/date/company filters.
- [ ] Add deadlines, follow-up dates, notes, contacts, and next-action reminders.
- [ ] Provide board and table views, plus quick status changes.
- [ ] Show useful progress indicators such as resume selected, match current/stale, draft ready, and follow-up due.

#### Resume and tailoring experience

- [ ] Show parsed resume sections in an editable editor rather than exposing raw extracted text mainly as a debug panel.
- [ ] Add side-by-side original/tailored diffs with accept, reject, edit, lock, and regenerate controls.
- [ ] Make the full draft editable before export and add autosave plus an explicit saved indicator.
- [ ] Show source citations inline and allow users to correct evidence when an output is wrong.
- [ ] Add template choice, section ordering, page-length feedback, and a true print/PDF preview.
- [ ] Improve mobile behavior so the resume preview does not depend on a 720px minimum-width canvas.

#### Feedback, accessibility, and resilience

- [ ] Replace generic error messages and expected 404 console noise with specific empty, retry, offline, and expired-session states.
- [ ] Add success feedback for saves, parsing, generation, and downloads.
- [ ] Preserve form inputs after failures and warn before navigating away with unsaved edits.
- [ ] Add accessible labels, focus management, keyboard operation, contrast checks, and screen-reader announcements for long-running tasks.
- [ ] Add frontend error boundaries, loading skeletons at route level, and observability for failed user flows.

Acceptance criteria:

- A new user can reach a grounded tailored draft without documentation.
- Every AI-generated field that affects export can be edited or rejected.
- The UI clearly communicates selected resume, source freshness, generation progress, save status, and export readiness.
- Core flows pass keyboard-only and automated accessibility checks at mobile and desktop widths.

### Phase 6 — Testing, observability, and operations

Goal: make releases safe and AI behavior measurable in production.

- [ ] Add backend unit tests for parsing normalization, chunking, keyword ranking, rank fusion, claim validation, and export behavior.
- [ ] Add database integration tests with PostgreSQL/pgvector for ownership filters, cascades, uniqueness, vector ranking, and migrations.
- [ ] Add API tests for every success, validation, authorization, not-found, and upstream-failure path.
- [ ] Add frontend component tests for editors and state transitions, plus end-to-end tests for sign-in -> upload -> application -> match -> tailor -> edit -> export.
- [ ] Mock model responses in CI and contract-test every structured output schema.
- [ ] Add request IDs, structured logs, traces, error monitoring, and dashboards for latency, failure rate, job queue depth, token usage, and cost per completed draft.
- [ ] Add per-user and per-IP rate limits, quotas, abuse controls, and budget alerts for URL parsing, analysis, matching, tailoring, and export.
- [ ] Define backups, restore tests, data retention, account deletion, export cleanup, and incident response.
- [ ] Pin backend dependency versions and automate dependency/security scanning.

Release gates:

- CI runs without live external services and covers the critical user journey.
- Authorization tests cover every endpoint that reads or writes user data.
- No known critical/high security findings are open.
- Database restore and account deletion procedures have been tested.
- AI latency, cost, failure rate, retrieval quality, and grounding metrics are visible.

## Recommended delivery order

1. Phase 0 safety fixes and migrations.
2. Phase 1 authentication plus complete ownership scoping.
3. Phase 2 multiple resumes and evidence management.
4. Phase 3 retrieval evaluation, tenant-safe hybrid search, citations, and grounding.
5. Phase 4 structured matching, editable/versioned generation, and background jobs.
6. Phase 5 guided UI redesign.
7. Phase 6 runs throughout all phases and becomes a release gate before broader launch.

Authentication should not be postponed behind UI polish or RAG tuning. Retrieval work must happen after ownership fields exist so indexes, filters, evaluation fixtures, and service APIs are designed correctly once.

## Near-term implementation slice

The first shippable slice should be small enough to review but foundational enough to reduce risk:

- [ ] Add Alembic and create a `users` table.
- [ ] Add nullable `user_id` columns through a migration, backfill legacy data to an explicit seed user, then make ownership non-null.
- [ ] Integrate one OIDC provider and implement `get_current_user`.
- [ ] Protect and scope application, resume, match, tailored-resume, full-draft, project-evidence, retrieval, and export routes.
- [ ] Add cross-user authorization tests for all resource families.
- [ ] Remove hard-coded skills and export only saved drafts.
- [ ] Add a minimal signed-in app shell with account/sign-out controls.

Definition of done for this slice: two test users can complete the current RolePilot workflow independently, neither can discover or affect the other's data by changing IDs, and the downloaded resume exactly matches the saved preview.

## Decisions to record before implementation

Create short architecture decision records for:

- Authentication provider and token/session flow between Next.js and FastAPI.
- Ownership model and whether PostgreSQL row-level security is enabled at launch.
- Legacy data ownership and personal seed/evaluation data handling.
- Original resume file storage and retention.
- Background job system and job status API.
- Retrieval stack: PostgreSQL full-text search plus pgvector, reranker choice, and index type.
- Artifact versioning and the source-of-truth draft used for export.
- AI model/prompt versioning and cost/quality evaluation policy.

## Product-level success metrics

- Activation: percentage of new users who upload a resume, save a job, and generate a first grounded draft.
- Time to value: median time from sign-up to first reviewed tailored draft.
- Quality: percentage of generated bullets accepted with no edit, accepted after edit, or rejected.
- Trust: unsupported-claim rate, citation-validity rate, and user-reported factual corrections.
- Retrieval: held-out Recall@5, nDCG@5, zero-result rate, and citation coverage.
- Reliability: successful completion rate and P95 latency for analysis, match, tailor, and export.
- Retention: users returning to tailor for another application within 30 days.
- Cost: AI and infrastructure cost per successfully exported resume.

## Explicit non-goals for the next release

- Automatic job application submission.
- Scraping authenticated job boards or bypassing anti-bot controls.
- Social/community features or public resume sharing.
- Training a custom foundation model before retrieval and grounding are measured.
- Complex team/organization tenancy; start with one private workspace per individual user.
- Automated claims about interview probability or guaranteed ATS outcomes.
