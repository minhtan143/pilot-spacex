"""FastAPI router: /api/v1/auth/* — user-facing auth endpoints."""

from __future__ import annotations

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from authcore.api.dependencies.auth import CurrentUser, get_current_user
from authcore.api.v1.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    VerifyEmailResponse,
)
from authcore.application.services.auth.change_password_service import (
    ChangePasswordPayload,
    ChangePasswordService,
)
from authcore.application.services.auth.forgot_password_service import (
    ForgotPasswordPayload,
    ForgotPasswordService,
)
from authcore.application.services.auth.login_service import LoginPayload, LoginService
from authcore.application.services.auth.logout_all_service import LogoutAllPayload, LogoutAllService
from authcore.application.services.auth.logout_service import LogoutPayload, LogoutService
from authcore.application.services.auth.refresh_token_service import (
    RefreshTokenPayload,
    RefreshTokenService,
)
from authcore.application.services.auth.register_service import RegisterPayload, RegisterService
from authcore.application.services.auth.resend_verification_service import (
    ResendVerificationPayload,
    ResendVerificationService,
)
from authcore.application.services.auth.reset_password_service import (
    ResetPasswordPayload,
    ResetPasswordService,
)
from authcore.application.services.auth.verify_email_service import (
    VerifyEmailPayload,
    VerifyEmailService,
)
from authcore.config import Settings
from authcore.container.container import Container
from authcore.external.rate_limiter import LoginRateLimiter
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.database.repositories.audit_log_repository import AuditLogRepository
from authcore.infrastructure.database.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from authcore.infrastructure.database.repositories.user_repository import UserRepository
from authcore.infrastructure.email.email_service import AbstractEmailService
from authcore.infrastructure.tokens.jwt_service import JWTService

router = APIRouter(prefix="/auth", tags=["auth"])


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@inject
async def register(
    body: RegisterRequest,
    request: Request,
    session_factory: async_sessionmaker[AsyncSession] = Depends(  # type: ignore[type-arg]
        Provide[Container.infra.session_factory]  # type: ignore[misc]
    ),
    redis_client: RedisClient = Depends(Provide[Container.infra.redis_client]),  # type: ignore[misc]
    email_service: AbstractEmailService = Depends(Provide[Container.infra.email_service]),  # type: ignore[misc]
    settings: Settings = Depends(Provide[Container.config]),  # type: ignore[misc]
) -> RegisterResponse:
    async with session_factory() as session:
        async with session.begin():
            svc = RegisterService(
                user_repo=UserRepository(session),
                redis_client=redis_client,
                email_service=email_service,
                settings=settings,
            )
            result = await svc.execute(
                RegisterPayload(email=body.email, password=body.password, ip_address=_ip(request))
            )
    return RegisterResponse(
        user_id=result.user_id,
        email=result.email,
        verification_sent=result.verification_sent,
    )


@router.get("/verify-email", response_model=VerifyEmailResponse)
@inject
async def verify_email(
    token: str,
    session_factory: async_sessionmaker[AsyncSession] = Depends(  # type: ignore[type-arg]
        Provide[Container.infra.session_factory]  # type: ignore[misc]
    ),
    redis_client: RedisClient = Depends(Provide[Container.infra.redis_client]),  # type: ignore[misc]
) -> VerifyEmailResponse:
    async with session_factory() as session:
        async with session.begin():
            svc = VerifyEmailService(
                user_repo=UserRepository(session),
                redis_client=redis_client,
            )
            result = await svc.execute(VerifyEmailPayload(token=token))
    return VerifyEmailResponse(user_id=result.user_id, email=result.email)


@router.post("/resend-verification", response_model=MessageResponse)
@inject
async def resend_verification(
    current_user: CurrentUser = Depends(get_current_user),
    session_factory: async_sessionmaker[AsyncSession] = Depends(  # type: ignore[type-arg]
        Provide[Container.infra.session_factory]  # type: ignore[misc]
    ),
    redis_client: RedisClient = Depends(Provide[Container.infra.redis_client]),  # type: ignore[misc]
    email_service: AbstractEmailService = Depends(Provide[Container.infra.email_service]),  # type: ignore[misc]
    settings: Settings = Depends(Provide[Container.config]),  # type: ignore[misc]
) -> MessageResponse:
    async with session_factory() as session:
        async with session.begin():
            svc = ResendVerificationService(
                user_repo=UserRepository(session),
                redis_client=redis_client,
                email_service=email_service,
                settings=settings,
            )
            await svc.execute(ResendVerificationPayload(user_id=current_user.user_id))
    return MessageResponse(message="Verification email sent")


@router.post("/login", response_model=LoginResponse)
@inject
async def login(
    body: LoginRequest,
    request: Request,
    session_factory: async_sessionmaker[AsyncSession] = Depends(  # type: ignore[type-arg]
        Provide[Container.infra.session_factory]  # type: ignore[misc]
    ),
    jwt_service: JWTService = Depends(Provide[Container.infra.jwt_service]),  # type: ignore[misc]
    login_rate_limiter: LoginRateLimiter = Depends(Provide[Container.login_rate_limiter]),  # type: ignore[misc]
    settings: Settings = Depends(Provide[Container.config]),  # type: ignore[misc]
) -> LoginResponse:
    async with session_factory() as session:
        async with session.begin():
            svc = LoginService(
                user_repo=UserRepository(session),
                token_repo=RefreshTokenRepository(session),
                audit_repo=AuditLogRepository(session),
                jwt_service=jwt_service,
                rate_limiter=login_rate_limiter,
                settings=settings,
            )
            result = await svc.execute(
                LoginPayload(email=body.email, password=body.password, ip_address=_ip(request))
            )
    return LoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        user_id=result.user_id,
        role=result.role,
    )


@router.post("/refresh", response_model=RefreshResponse)
@inject
async def refresh_token(
    body: RefreshRequest,
    request: Request,
    session_factory: async_sessionmaker[AsyncSession] = Depends(  # type: ignore[type-arg]
        Provide[Container.infra.session_factory]  # type: ignore[misc]
    ),
    jwt_service: JWTService = Depends(Provide[Container.infra.jwt_service]),  # type: ignore[misc]
    settings: Settings = Depends(Provide[Container.config]),  # type: ignore[misc]
) -> RefreshResponse:
    async with session_factory() as session:
        async with session.begin():
            svc = RefreshTokenService(
                user_repo=UserRepository(session),
                token_repo=RefreshTokenRepository(session),
                audit_repo=AuditLogRepository(session),
                jwt_service=jwt_service,
                settings=settings,
            )
            result = await svc.execute(
                RefreshTokenPayload(
                    raw_refresh_token=body.refresh_token, ip_address=_ip(request)
                )
            )
    return RefreshResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        user_id=result.user_id,
    )


@router.post("/logout", response_model=MessageResponse)
@inject
async def logout(
    body: RefreshRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session_factory: async_sessionmaker[AsyncSession] = Depends(  # type: ignore[type-arg]
        Provide[Container.infra.session_factory]  # type: ignore[misc]
    ),
    redis_client: RedisClient = Depends(Provide[Container.infra.redis_client]),  # type: ignore[misc]
    settings: Settings = Depends(Provide[Container.config]),  # type: ignore[misc]
) -> MessageResponse:
    async with session_factory() as session:
        async with session.begin():
            svc = LogoutService(
                token_repo=RefreshTokenRepository(session),
                audit_repo=AuditLogRepository(session),
                redis_client=redis_client,
                settings=settings,
            )
            await svc.execute(
                LogoutPayload(
                    raw_refresh_token=body.refresh_token,
                    jti=current_user.jti,
                    user_id=current_user.user_id,
                    ip_address=_ip(request),
                )
            )
    return MessageResponse(message="Logged out successfully")


@router.post("/logout-all", response_model=MessageResponse)
@inject
async def logout_all(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session_factory: async_sessionmaker[AsyncSession] = Depends(  # type: ignore[type-arg]
        Provide[Container.infra.session_factory]  # type: ignore[misc]
    ),
) -> MessageResponse:
    async with session_factory() as session:
        async with session.begin():
            svc = LogoutAllService(
                token_repo=RefreshTokenRepository(session),
                audit_repo=AuditLogRepository(session),
            )
            await svc.execute(
                LogoutAllPayload(
                    user_id=current_user.user_id, ip_address=_ip(request)
                )
            )
    return MessageResponse(message="All sessions revoked")


@router.post("/change-password", response_model=MessageResponse)
@inject
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session_factory: async_sessionmaker[AsyncSession] = Depends(  # type: ignore[type-arg]
        Provide[Container.infra.session_factory]  # type: ignore[misc]
    ),
) -> MessageResponse:
    async with session_factory() as session:
        async with session.begin():
            svc = ChangePasswordService(
                user_repo=UserRepository(session),
                token_repo=RefreshTokenRepository(session),
                audit_repo=AuditLogRepository(session),
            )
            await svc.execute(
                ChangePasswordPayload(
                    user_id=current_user.user_id,
                    current_password=body.current_password,
                    new_password=body.new_password,
                    ip_address=_ip(request),
                )
            )
    return MessageResponse(message="Password changed successfully")


@router.post("/forgot-password", response_model=MessageResponse)
@inject
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    session_factory: async_sessionmaker[AsyncSession] = Depends(  # type: ignore[type-arg]
        Provide[Container.infra.session_factory]  # type: ignore[misc]
    ),
    redis_client: RedisClient = Depends(Provide[Container.infra.redis_client]),  # type: ignore[misc]
    email_service: AbstractEmailService = Depends(Provide[Container.infra.email_service]),  # type: ignore[misc]
    settings: Settings = Depends(Provide[Container.config]),  # type: ignore[misc]
) -> MessageResponse:
    async with session_factory() as session:
        async with session.begin():
            svc = ForgotPasswordService(
                user_repo=UserRepository(session),
                redis_client=redis_client,
                email_service=email_service,
                settings=settings,
            )
            await svc.execute(
                ForgotPasswordPayload(email=body.email, ip_address=_ip(request))
            )
    return MessageResponse(message="If that email exists, a reset link was sent")


@router.post("/reset-password", response_model=MessageResponse)
@inject
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    session_factory: async_sessionmaker[AsyncSession] = Depends(  # type: ignore[type-arg]
        Provide[Container.infra.session_factory]  # type: ignore[misc]
    ),
    redis_client: RedisClient = Depends(Provide[Container.infra.redis_client]),  # type: ignore[misc]
) -> MessageResponse:
    async with session_factory() as session:
        async with session.begin():
            svc = ResetPasswordService(
                user_repo=UserRepository(session),
                token_repo=RefreshTokenRepository(session),
                audit_repo=AuditLogRepository(session),
                redis_client=redis_client,
            )
            await svc.execute(
                ResetPasswordPayload(
                    token=body.token,
                    new_password=body.new_password,
                    ip_address=_ip(request),
                )
            )
    return MessageResponse(message="Password reset successfully")
