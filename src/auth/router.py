from fastapi import APIRouter, Depends, status

from src.auth.schemas import (
    TokenResponseSchema,
    LoginRequestSchema,
    Auth0TokenRequestSchema,
    RegisterRequestSchema,
    RegisterResponseSchema,
)
from src.auth.service import AuthService
from src.core.dependencies import get_current_user, get_auth_service
from src.users.models import User
from src.users.schemas import UserResponseSchema

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequestSchema,
    service: AuthService = Depends(get_auth_service),
):
    return await service.register(data=data)


@router.post("/login", response_model=TokenResponseSchema)
async def login(
    data: LoginRequestSchema, service: AuthService = Depends(get_auth_service)
):
    token = await service.login(email=data.email, password=data.password)
    return TokenResponseSchema(access_token=token)


@router.post("/login/auth0", response_model=TokenResponseSchema)
async def login_auth0(
    data: Auth0TokenRequestSchema,
    service: AuthService = Depends(get_auth_service),
):
    token = await service.login_auth0(auth0_token=data.token)
    return TokenResponseSchema(access_token=token)


@router.get("/me", response_model=UserResponseSchema)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
