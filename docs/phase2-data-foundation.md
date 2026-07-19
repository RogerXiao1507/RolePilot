# Phase 2 data foundation

Phase 2 replaces RolePilot's single "latest resume" assumption with a versioned,
user-managed source library.

## Resume lifecycle

- A user may upload multiple PDF resumes, label them, choose one default, and
  archive, restore, or permanently delete each resume.
- Every application stores its own `selected_resume_id`. Match, tailor, draft,
  and export routes reject a different resume even when both records belong to
  the same user.
- Parsed contact, education, experience, projects, skills, and other sections
  are editable. Saving parsed changes increments the resume version, refreshes
  stable source items, and marks dependent matches and drafts stale.
- Tailored bullets store citations containing a source type, stable source ID,
  and source version. Server-side validation drops citations outside the current
  user's source catalog and rejects uncited bullets when sources are available.

## Private original PDF storage

The original PDF is stored outside PostgreSQL in a private S3-compatible bucket.
PostgreSQL stores only its opaque object key and the derived text needed by the
product. Object keys contain the internal user UUID and a random UUID, not the
original filename.

Configure these variables on the backend service (Render), never in Vercel:

```env
OBJECT_STORAGE_BUCKET=rolepilot-private
OBJECT_STORAGE_REGION=us-east-1
OBJECT_STORAGE_ACCESS_KEY_ID=...
OBJECT_STORAGE_SECRET_ACCESS_KEY=...
OBJECT_STORAGE_SIGNED_URL_SECONDS=300
OBJECT_STORAGE_SSE_ALGORITHM=AES256
OBJECT_STORAGE_REQUIRED=true
```

For Cloudflare R2, Backblaze B2, MinIO, or another S3-compatible service, also
set `OBJECT_STORAGE_ENDPOINT_URL`. For AWS S3, leave it unset.

The bucket must block public access. The access key should be scoped to object
read/write/delete operations on this bucket only. Uploads request server-side
encryption, and original-PDF reads use authenticated, five-minute signed URLs.
Setting `OBJECT_STORAGE_REQUIRED=true` makes production startup fail when the
bucket or credentials are absent instead of silently accepting unprotected
uploads.

Local development may leave storage unset and keep
`OBJECT_STORAGE_REQUIRED=false`; analysis and structured persistence still work,
but the original-PDF link is unavailable. Use a local MinIO bucket when testing
the complete storage flow.

## Evidence lifecycle

- Evidence supports outcomes, dates, skills, keywords, links, bullets, and
  user-verified metrics.
- A parsed resume bullet can be converted into evidence while retaining its
  stable source link.
- AI-suggested metrics are stored separately and are not embedded as verified
  metrics until the user explicitly confirms one.
- Create, edit, confirm, and retry operations move ingestion through `pending`,
  `ready`, or `failed`. Retrieval only considers `ready` evidence.
- Evidence changes increment its version and mark dependent tailored/full drafts
  stale.

## Deployment sequence

1. Create and lock down the private object-storage bucket.
2. Add the object-storage variables to Render and set
   `OBJECT_STORAGE_REQUIRED=true`.
3. Deploy the backend. Its startup command applies Alembic revisions `0004` and
   `0005` before starting FastAPI.
4. Deploy the frontend. Phase 2 adds no browser-visible secrets or new Vercel
   environment variables.
5. Smoke-test two resumes, application selection, parsed-data editing, evidence
   ingestion, stale-state blocking, and a signed original-PDF link.
