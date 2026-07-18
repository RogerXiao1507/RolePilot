# ADR 0001: Auth0 authentication with a token-mediating frontend

- Status: Accepted
- Date: 2026-07-18
- Phase: 1 — Per-user authentication and data isolation

## Context

RolePilot currently has a Next.js browser application and a separate FastAPI resource server. The existing API is effectively single-user: it accepts requests without authentication and queries shared tables without an ownership predicate.

Adding a login screen alone would not create a security boundary. The browser session, FastAPI token validation, database ownership model, retrieval filters, and legacy-data migration must all agree on one authenticated identity.

## Decision

Use Auth0 as the initial managed OpenID Connect provider and use its Authorization Code flow through `@auth0/nextjs-auth0`.

The Next.js application will act as a token-mediating backend:

1. Auth0 stores the login session in encrypted, HTTP-only, secure cookies managed by the Next.js SDK.
2. Browser code calls a same-origin Next.js `/api/backend/*` route instead of receiving an API access token.
3. The Next.js route obtains the Auth0 access token on the server and forwards it to FastAPI as `Authorization: Bearer <token>`.
4. The SDK's browser-facing `/auth/access-token` endpoint is disabled.
5. FastAPI independently validates every access token's signature, algorithm, issuer, audience, expiry, and subject against Auth0's JWKS. It never accepts a user ID supplied by the browser.
6. FastAPI maps the immutable OIDC `sub` claim to an internal UUID in the `users` table and applies that UUID to every owned query and write.
7. Protected frontend routes improve navigation and session UX, but FastAPI remains the authoritative security boundary.

Public routes are limited to health/root endpoints and the Auth0 login, callback, logout, and session endpoints required by the SDK. Application, resume, evidence, matching, generation, and export routes require a valid API token.

## Token and session configuration

- The Auth0 API identifier is the access-token audience and must match `AUTH0_AUDIENCE` in both frontend and backend configuration.
- The backend issuer must be the tenant's exact HTTPS issuer, including its trailing slash.
- Only asymmetric `RS256` access tokens are accepted.
- Authentication configuration has no production bypass and no fallback shared secret.
- Session cookies are HTTP-only, `SameSite=Lax`, and secure outside local HTTP development.
- Redirect targets remain same-origin; arbitrary `returnTo` URLs are not trusted.
- Token refresh is handled server-side by the Auth0 SDK. A failed or expired session returns 401 and the UI directs the user to sign in again.

## User and ownership model

The internal `users.id` UUID is the database ownership key. `users.external_subject` is unique and stores the complete Auth0 `sub`; email is profile data and is not an ownership key because it can change.

Direct ownership is stored on applications, resumes, project evidence, evidence chunks, matches, tailored resumes, and full resume drafts. Related resources must have the same `user_id`. API queries include `user_id` before selecting by an externally supplied ID. Missing and foreign-owned resources both produce a non-disclosing 404.

Retrieval filters by `project_evidence_chunks.user_id` before vector or lexical ranking. PostgreSQL row-level security is added as defense in depth, using a transaction-local `app.current_user_id` value set by the authenticated database dependency. Application-level ownership checks remain mandatory.

## Legacy-data policy

Existing global rows are assigned to one deterministic, disabled migration principal (`legacy|rolepilot-owner`) during the schema migration. They are not automatically attached to the first account, matched by email, or exposed to newly registered users.

An operator may explicitly transfer that principal's rows to a verified Auth0 subject using a dedicated administrative migration command. If production legacy data is not needed, the operator should delete it before onboarding users. This makes the ownership decision explicit and auditable.

Personal development seed and evaluation records are not shipped as default product data. Public examples must be synthetic or de-identified.

## Account deletion

Deleting an account deletes its owned database records through foreign-key cascades. External Auth0 account deletion is a separate identity-provider operation and is documented as such; RolePilot must not claim to delete the provider account when it only deletes workspace data.

## Consequences

Benefits:

- RolePilot does not store passwords or implement account recovery.
- Access tokens are not exposed to ordinary browser JavaScript.
- FastAPI can be tested and enforced as an independent resource server.
- Internal ownership stays stable if a user's email or display name changes.

Tradeoffs:

- Local and deployed environments require an Auth0 application and API configuration.
- The Next.js proxy adds one network hop.
- Auth0 availability and pricing become external dependencies.
- A future provider migration requires preserving or explicitly remapping external subjects, while internal user UUIDs and owned rows can remain unchanged.

## Rejected alternatives

- **Frontend-only route protection:** rejected because direct FastAPI requests would remain unauthenticated and shared queries would still leak data.
- **Passing a browser-supplied user ID:** rejected because it is trivially forgeable.
- **Giving the SPA direct access tokens:** rejected for this application because a server-side proxy can keep tokens out of browser JavaScript with little added complexity.
- **Building local password authentication now:** rejected because password hashing, verification, recovery, email verification, abuse prevention, and session revocation would substantially expand the security surface.
- **Email as the ownership key:** rejected because email addresses can change and are not the immutable OIDC principal identifier.
