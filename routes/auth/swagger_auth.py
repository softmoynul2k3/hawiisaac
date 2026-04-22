from datetime import date
from typing import Optional

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, Response
from pydantic import BaseModel
from pydantic import EmailStr
from fastapi.security import OAuth2PasswordRequestForm

from app.config import settings
from applications.user.models import User
from app.token import (
    get_current_user,
    create_access_token,
    create_refresh_token,
    set_auth_cookies,
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
)
from tortoise.contrib.pydantic import pydantic_model_creator
import re

router = APIRouter(tags=["Swagger Authentication"])


async def detect_input_type(value: str) -> str:
    value = value.strip()
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'

    if re.match(email_regex, value):
        return 'email'
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Email address.")


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _build_token_data(user: User) -> dict:
    return {
        "sub": str(user.id),
        "email": user.email or "",
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
    }


class OAuth2EmailPasswordForm:
    def __init__(
            self,
            email: EmailStr = Form(...),
            password: str = Form(...),
            scope: str = Form(""),
            client_id: str = Form(None),
            client_secret: str = Form(None),
    ):
        self.email = email
        self.password = password
        self.scopes = scope.split()
        self.client_id = client_id
        self.client_secret = client_secret


User_Pydantic = pydantic_model_creator(User, name="User")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


@router.post("/swagger_login_auth2", response_model=TokenResponse)
async def login_auth2(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    email = _normalize_email(form_data.username)
    await detect_input_type(email)

    user = await User.get_or_none(email=email)  # <- use username as email
    if not user or not user.verify_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    token_data = _build_token_data(user)

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    set_auth_cookies(response, access_token, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

@router.get("/swagger-auth-token")
async def swagger_auth_token(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
):
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")

    if hasattr(request.state, "new_tokens"):
        access_token = request.state.new_tokens["access_token"]
        refresh_token = request.state.new_tokens["refresh_token"]
        set_auth_cookies(
            response,
            request.state.new_tokens["access_token"],
            request.state.new_tokens["refresh_token"],
        )

    return {"access_token": access_token, "refresh_token": refresh_token}


@router.post("/logout")
async def logout(response: Response):
    # Clear cookies in a browser-compatible way by both deleting and expiring.
    cookie_secure = not settings.DEBUG
    for cookie_name in (ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME):
        response.delete_cookie(key=cookie_name, path="/")
        response.set_cookie(
            key=cookie_name,
            value="",
            max_age=0,
            expires=0,
            path="/",
            secure=cookie_secure,
            httponly=True,
            samesite="lax",
        )
    response.headers["Clear-Site-Data"] = "\"cookies\", \"storage\""
    return {"status": "success", "message": "Logged out successfully"}


