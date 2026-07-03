"""User Service — FastAPI router."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field

from scholarscout.contexts.users.application.auth_service import AuthService, decode_access_token
from scholarscout.shared.domain.exceptions import ValidationError as DomainValidationError

router = APIRouter(prefix="/auth", tags=["Authentication"])
users_router = APIRouter(prefix="/users", tags=["Users"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(default="", max_length=256)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class RefreshRequest(BaseModel):
    refresh_token: str


async def _get_auth_service():
    from scholarscout.api.deps import get_auth_service, get_db
    async for session in get_db():
        yield get_auth_service(session)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    try:
        user = await service.register(
            email=str(body.email),
            password=body.password,
            name=body.name,
        )
        access_token, refresh_token = await service.login(str(body.email), body.password)
    except DomainValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message) from e

    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 24 * 3600,
    )
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    try:
        access_token, refresh_token = await service.login(str(body.email), body.password)
    except DomainValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 24 * 3600,
    )
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    response: Response,
    service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    try:
        access_token, new_refresh = await service.refresh(body.refresh_token)
    except DomainValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        ) from e

    response.set_cookie(
        "refresh_token",
        new_refresh,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 24 * 3600,
    )
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    body: RefreshRequest,
    service: AuthService = Depends(_get_auth_service),
) -> dict:
    await service.logout(body.refresh_token)
    return {"message": "Logged out"}
