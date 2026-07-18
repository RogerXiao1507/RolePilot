from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
import jwt
import pytest

from app.api.deps import get_current_user
from app.core.auth import AccessTokenClaims, AccessTokenVerifier
from app.main import app


ISSUER = "https://rolepilot-test.auth0.com/"
AUDIENCE = "https://api.rolepilot.test"


@pytest.fixture(scope="module")
def signing_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def token_payload(**overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "auth0|token-test",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    payload.update(overrides)
    return payload


def verifier_with_key(public_key) -> AccessTokenVerifier:
    verifier = AccessTokenVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url=f"{ISSUER}.well-known/jwks.json",
    )
    verifier.jwks_client.get_signing_key_from_jwt = lambda _token: SimpleNamespace(
        key=public_key
    )
    return verifier


def test_valid_rs256_access_token_is_accepted(signing_keys):
    private_key, public_key = signing_keys
    token = jwt.encode(token_payload(), private_key, algorithm="RS256")

    claims = verifier_with_key(public_key).verify(token)

    assert claims.sub == "auth0|token-test"
    assert claims.iss == ISSUER
    assert claims.aud == AUDIENCE


@pytest.mark.parametrize(
    "payload_changes",
    [
        {"exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        {"iss": "https://wrong-issuer.example/"},
        {"aud": "https://wrong-audience.example"},
    ],
    ids=["expired", "wrong-issuer", "wrong-audience"],
)
def test_invalid_token_claims_are_rejected(signing_keys, payload_changes):
    private_key, public_key = signing_keys
    token = jwt.encode(
        token_payload(**payload_changes), private_key, algorithm="RS256"
    )

    with pytest.raises(HTTPException) as exc_info:
        verifier_with_key(public_key).verify(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_malformed_token_is_rejected(signing_keys):
    _, public_key = signing_keys

    with pytest.raises(HTTPException) as exc_info:
        verifier_with_key(public_key).verify("not-a-jwt")

    assert exc_info.value.status_code == 401


def test_non_rs256_algorithm_is_rejected(signing_keys):
    _, public_key = signing_keys
    token = jwt.encode(token_payload(), "symmetric-secret-that-is-at-least-32-bytes", algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        verifier_with_key(public_key).verify(token)

    assert exc_info.value.status_code == 401


def test_quarantined_legacy_subject_cannot_authenticate():
    now = datetime.now(timezone.utc)
    claims = AccessTokenClaims(
        sub="legacy|rolepilot-owner",
        iss=ISSUER,
        aud=AUDIENCE,
        iat=int(now.timestamp()),
        exp=int((now + timedelta(minutes=5)).timestamp()),
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(claims=claims, db=SimpleNamespace())

    assert exc_info.value.status_code == 403


def test_every_protected_route_rejects_an_unauthenticated_request():
    app.dependency_overrides.pop(get_current_user, None)
    client = TestClient(app)
    public_paths = {"/", "/health", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    checked: list[str] = []

    for route_path, operations in app.openapi()["paths"].items():
        if route_path in public_paths:
            continue
        path = (
            route_path.replace("{application_id}", "1")
            .replace("{project_id}", "1")
        )
        for method in sorted(operations):
            if method.upper() in {"HEAD", "OPTIONS", "PARAMETERS"}:
                continue
            response = client.request(method.upper(), path)
            assert response.status_code == 401, f"{method.upper()} {route_path} was not protected"
            checked.append(f"{method.upper()} {route_path}")

    assert checked
