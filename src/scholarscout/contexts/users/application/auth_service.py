"""
Authentication Service — JWT token management and password hashing.

Token strategy:
- Short-lived access tokens (60 min) stored in memory/cookie
- Long-lived refresh tokens (30 days) stored in Redis + DB
- Refresh token rotation on every use (prevents token theft)
- Refresh tokens are hashed in Redis (prevent Redis dump attack)

Security posture:
- bcrypt with work factor 12 (adjustable)
- Constant-time password comparison (passlib handles this)
- JWT signed with HS256 (symmetric — no PKI needed for monolith)
  TODO: Switch to RS256 when extracting to separate auth service
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scholarscout.config import settings
from scholarscout.contexts.users.infrastructure.models import UserModel
from scholarscout.shared.domain.exceptions import (
    EntityNotFoundError,
    ValidationError,
)
from scholarscout.shared.infrastructure.cache.redis_client import CacheClient

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

REFRESH_TOKEN_TTL = timedelta(days=settings.auth.refresh_token_expire_days)
ACCESS_TOKEN_TTL = timedelta(minutes=settings.auth.access_token_expire_minutes)


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + ACCESS_TOKEN_TTL,
        "type": "access",
    }
    return jwt.encode(payload, settings.auth.secret_key, algorithm=settings.auth.algorithm)


def create_refresh_token() -> str:
    """Cryptographically random opaque refresh token."""
    return secrets.token_urlsafe(64)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.auth.secret_key,
            algorithms=[settings.auth.algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise ValidationError("token", "Access token has expired")
    except jwt.InvalidTokenError as e:
        raise ValidationError("token", f"Invalid token: {e}")


class AuthService:
    def __init__(self, session: AsyncSession, cache: CacheClient) -> None:
        self._session = session
        self._cache = cache

    async def register(
        self,
        email: str,
        password: str,
        name: str = "",
    ) -> UserModel:
        # Check existing
        stmt = select(UserModel).where(UserModel.email == email.lower())
        result = await self._session.execute(stmt)
        if result.scalar_one_or_none():
            raise ValidationError("email", "Email already registered")

        if len(password) < 8:
            raise ValidationError("password", "Password must be at least 8 characters")

        now = datetime.now(UTC)
        user = UserModel(
            id=uuid.uuid4(),
            email=email.lower().strip(),
            hashed_password=hash_password(password),
            name=name.strip(),
            role="user",
            is_active=True,
            is_verified=False,
            verification_token=secrets.token_urlsafe(32),
            created_at=now,
            updated_at=now,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def login(self, email: str, password: str) -> tuple[str, str]:
        """Returns (access_token, refresh_token)."""
        stmt = select(UserModel).where(UserModel.email == email.lower())
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.hashed_password:
            raise ValidationError("credentials", "Invalid email or password")
        if not verify_password(password, user.hashed_password):
            raise ValidationError("credentials", "Invalid email or password")
        if not user.is_active:
            raise ValidationError("account", "Account is deactivated")

        user.last_login_at = datetime.now(UTC)
        await self._session.flush()

        access_token = create_access_token(user.id, user.role)
        refresh_token = await self._issue_refresh_token(user.id)
        return access_token, refresh_token

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        """Rotate refresh token and issue new access token."""
        user_id = await self._validate_refresh_token(refresh_token)
        if not user_id:
            raise ValidationError("token", "Invalid or expired refresh token")

        user = await self._session.get(UserModel, uuid.UUID(user_id))
        if not user or not user.is_active:
            raise ValidationError("token", "User not found or inactive")

        # Rotate: revoke old token, issue new
        await self._revoke_refresh_token(refresh_token)
        new_access = create_access_token(user.id, user.role)
        new_refresh = await self._issue_refresh_token(user.id)
        return new_access, new_refresh

    async def logout(self, refresh_token: str) -> None:
        await self._revoke_refresh_token(refresh_token)

    async def _issue_refresh_token(self, user_id: uuid.UUID) -> str:
        token = create_refresh_token()
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        await self._cache.set(
            f"refresh:{token_hash}",
            str(user_id),
            ttl=REFRESH_TOKEN_TTL,
        )
        return token

    async def _validate_refresh_token(self, token: str) -> str | None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return await self._cache.get(f"refresh:{token_hash}")

    async def _revoke_refresh_token(self, token: str) -> None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        await self._cache.delete(f"refresh:{token_hash}")
