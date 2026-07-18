from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings


bearer_scheme = HTTPBearer(auto_error=False)


class AccessTokenClaims(BaseModel):
    model_config = ConfigDict(extra="allow")

    sub: str = Field(min_length=1, max_length=255)
    iss: str
    aud: str | list[str]
    exp: int
    iat: int
    email: str | None = None
    name: str | None = None


class AccessTokenVerifier:
    def __init__(self, *, issuer: str, audience: str, jwks_url: str) -> None:
        self.issuer = issuer
        self.audience = audience
        self.jwks_client = PyJWKClient(
            jwks_url,
            cache_jwk_set=True,
            cache_keys=True,
            lifespan=300,
            timeout=5,
        )

    def verify(self, token: str) -> AccessTokenClaims:
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            payload: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["sub", "iss", "aud", "exp", "iat"]},
            )
            return AccessTokenClaims.model_validate(payload)
        except (jwt.PyJWTError, ValueError) as exc:
            raise invalid_token_error() from exc


def invalid_token_error(detail: str = "Invalid or expired access token.") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


@lru_cache(maxsize=1)
def get_access_token_verifier() -> AccessTokenVerifier:
    return AccessTokenVerifier(
        issuer=settings.auth_issuer,
        audience=settings.auth_audience,
        jwks_url=settings.resolved_auth_jwks_url,
    )


def get_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AccessTokenClaims:
    if credentials is None:
        raise invalid_token_error("Authentication required.")
    if credentials.scheme.lower() != "bearer":
        raise invalid_token_error()
    return get_access_token_verifier().verify(credentials.credentials)
