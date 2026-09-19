from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse, StandardResponse
from app.schemas.user import UserResponse, UserUpdateProfileRequest
from app.services.auth_service import AuthService
from app.utils.api_response import make_response

router = APIRouter()


@router.post(
    "/signup",
    response_model=StandardResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def signup(
    data: SignupRequest,
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[UserResponse]:
    user = await AuthService.register(db, data)
    return make_response(
        data=user,
        message="User account created successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.post(
    "/login",
    response_model=StandardResponse[TokenResponse],
    summary="Authenticate user and issue JWT tokens",
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[TokenResponse]:
    tokens = await AuthService.login(db, data)
    return make_response(data=tokens, message="Login successful")


@router.post(
    "/refresh-token",
    response_model=StandardResponse[TokenResponse],
    summary="Refresh an expired access token using a valid refresh token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[TokenResponse]:
    tokens = await AuthService.refresh_access_token(db, data)
    return make_response(data=tokens, message="Token refreshed successfully")


@router.post(
    "/forgot-password",
    response_model=StandardResponse[dict],
    summary="Request a password reset link and token",
)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    token = await AuthService.request_password_reset(db, data)
    return make_response(
        data={"reset_token": token},
        message="Password reset instructions processed",
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password using a valid reset token",
)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await AuthService.reset_password(db, data)
    return MessageResponse(
        success=True,
        message="Password has been reset successfully. You can now login with your new password.",
    )


@router.get(
    "/me",
    response_model=StandardResponse[UserResponse],
    summary="Get authenticated user profile",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> StandardResponse[UserResponse]:
    return make_response(
        data=UserResponse.model_validate(current_user),
        message="Profile retrieved successfully",
    )


@router.put(
    "/me",
    response_model=StandardResponse[UserResponse],
    summary="Update authenticated user profile or change password",
)
async def update_my_profile(
    data: UserUpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[UserResponse]:
    updated_user = await AuthService.update_profile(db, current_user, data)
    return make_response(
        data=updated_user,
        message="Profile updated successfully",
    )
