# Authentication setup and data lifecycle

## Auth0 configuration

1. Create an Auth0 **Regular Web Application** for the Next.js frontend.
2. Add `http://localhost:3000/auth/callback` to Allowed Callback URLs.
3. Add `http://localhost:3000` to Allowed Logout URLs and Allowed Web Origins.
4. Create an Auth0 API with an identifier such as `https://api.rolepilot.example` and select RS256 signing.
5. Use that exact API identifier as `AUTH0_AUDIENCE` in both services.
6. Copy `frontend/.env.example` to `frontend/.env.local` and `backend/.env.example` to `backend/.env`, then fill the real values. Generate the frontend cookie secret with `openssl rand -hex 32`.
7. Apply the database migration with `cd backend && alembic upgrade head` before starting either service.

Production callback, logout, web-origin, issuer, base URL, and backend URL values must use the deployed HTTPS origins. Secrets belong in the deployment platform's secret store and must not be committed.

The frontend requests `offline_access` so the Auth0 SDK can refresh API tokens on the server. Enable refresh-token rotation for the Auth0 application. The browser receives only the encrypted, HTTP-only application session cookie; RolePilot disables the SDK access-token endpoint.

## Existing data

Migration `0003_user_ownership` quarantines all pre-authentication rows under the disabled subject `legacy|rolepilot-owner`. Those rows are invisible to normal accounts.

If all quarantined data is known to belong to one verified user, first have that user sign in, take a backup, and run this with database-owner migration credentials:

```bash
cd backend
python scripts/transfer_legacy_data.py \
  --target-subject 'auth0|exact-subject-from-auth0' \
  --confirm-transfer-legacy-data
```

If ownership is uncertain or the data is not needed, delete the legacy rows instead of transferring them. Never infer ownership from an email address.

## Retention and deletion

- RolePilot stores extracted resume text and its analysis in PostgreSQL. The current implementation does not retain the uploaded PDF after request processing.
- Applications, resumes, evidence, chunks, matches, tailored content, and full drafts remain until the user deletes the RolePilot account or an operator applies a documented retention policy.
- `DELETE /users/me` immediately deletes the internal user and all owned database rows through foreign-key cascades. It does not delete the separate Auth0 identity; users or operators must remove that identity in Auth0 when required.
- DOCX/PDF exports use unique temporary files and remove them after the response completes. The application does not keep a server-side export archive.
- Database backups may retain deleted rows until the infrastructure provider's configured backup-retention window expires. Production operators must document that window in the privacy notice.
- Personal seed files, database-derived evaluation exports, and embedding caches are excluded from the repository. Only synthetic/de-identified fixtures may be committed. Local exports use `*.local.json`, which Git ignores.
