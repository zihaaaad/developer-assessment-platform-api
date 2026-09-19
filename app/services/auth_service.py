from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_crypto_token,
    hash_password,
    verify_password,
)
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse, UserUpdateProfileRequest, UserUpdateRoleRequest


class AuthService:
    @staticmethod
    async def register(db: AsyncSession, data: SignupRequest) -> UserResponse:
        existing = await db.execute(select(User.id).where(User.email == data.email.lower()))
        if existing.scalar_one_or_none():
            raise ConflictException(message=f"An account with email '{data.email}' already exists")

        user = User(
            name=data.name.strip(),
            email=data.email.lower().strip(),
            password_hash=hash_password(data.password),
            role=data.role or RoleEnum.CANDIDATE,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return UserResponse.model_validate(user)

    @staticmethod
    async def login(db: AsyncSession, data: LoginRequest) -> TokenResponse:
        result = await db.execute(select(User).where(User.email == data.email.lower().strip()))
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.password_hash):
            raise UnauthorizedException(message="Incorrect email or password")

        access_token = create_access_token(subject=user.id, role=user.role.value)
        refresh_token = create_refresh_token(subject=user.id)

        user.refresh_token = refresh_token
        await db.flush()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    async def refresh_access_token(db: AsyncSession, data: RefreshTokenRequest) -> TokenResponse:
        payload = decode_token(data.refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedException(message="Invalid or expired refresh token")

        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or user.refresh_token != data.refresh_token:
            raise UnauthorizedException(message="Refresh token has been revoked or is invalid")

        access_token = create_access_token(subject=user.id, role=user.role.value)
        new_refresh = create_refresh_token(subject=user.id)

        user.refresh_token = new_refresh
        await db.flush()

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    async def request_password_reset(db: AsyncSession, data: ForgotPasswordRequest) -> str:
        result = await db.execute(select(User).where(User.email == data.email.lower().strip()))
        user = result.scalar_one_or_none()

        if not user:
            return "If the email is registered, password reset instructions have been dispatched."

        token = generate_crypto_token()
        user.password_reset_token = token
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        )
        await db.flush()
        return token

    @staticmethod
    async def reset_password(db: AsyncSession, data: ResetPasswordRequest) -> None:
        result = await db.execute(
            select(User).where(User.password_reset_token == data.token)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise BadRequestException(message="Invalid or expired password reset token")

        expires = user.password_reset_expires.replace(tzinfo=timezone.utc) if user.password_reset_expires.tzinfo is None else user.password_reset_expires
        if not expires or expires < datetime.now(timezone.utc):
            raise BadRequestException(message="Password reset token has expired")

        user.password_hash = hash_password(data.new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.refresh_token = None
        await db.flush()

    @staticmethod
    async def update_profile(
        db: AsyncSession, user: User, data: UserUpdateProfileRequest
    ) -> UserResponse:
        if data.name:
            user.name = data.name.strip()

        if data.new_password:
            if not data.current_password:
                raise BadRequestException(message="Current password is required to set a new password")
            if not verify_password(data.current_password, user.password_hash):
                raise BadRequestException(message="Current password does not match")
            user.password_hash = hash_password(data.new_password)

        await db.flush()
        await db.refresh(user)
        return UserResponse.model_validate(user)

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> UserResponse:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException(message=f"User '{user_id}' not found")
        return UserResponse.model_validate(user)

    @staticmethod
    async def update_user_role(
        db: AsyncSession, target_user_id: str, data: UserUpdateRoleRequest
    ) -> UserResponse:
        result = await db.execute(select(User).where(User.id == target_user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException(message=f"User '{target_user_id}' not found")

        user.role = data.role
        await db.flush()
        await db.refresh(user)
        return UserResponse.model_validate(user)

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: str) -> None:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException(message=f"User '{user_id}' not found")
        await db.delete(user)
        await db.flush()
