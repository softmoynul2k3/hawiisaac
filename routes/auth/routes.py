from typing import Optional
import re

from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from applications.user.models import User
from app.token import get_current_user, create_access_token, create_refresh_token
from app.utils.otp_manager import generate_otp, verify_otp, verify_session_key
from app.utils.social_auth import (
    get_or_create_social_user,
    verify_apple_id_token,
    verify_google_id_token,
)
from app.config import settings
router = APIRouter()


# ------------------------
# Helpers
# ------------------------
async def detect_input_type(value: str) -> str:
    value = value.strip()
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'

    if re.match(email_regex, value):
        return "email"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid email address",
    )


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _build_token_data(user: User) -> dict:
    return {
        "sub": str(user.id),
        "email": user.email or "",
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
    }


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class SocialAuthRequest(BaseModel):
    id_token: str


class AppleAuthRequest(BaseModel):
    id_token: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


def _build_auth_response(user: User, message: Optional[str] = None) -> dict:
    token_data = _build_token_data(user)
    response = {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "token_type": "bearer",
    }
    if message:
        response["message"] = message
    return response


# ------------------------
# LOGIN (OAuth2)
# ------------------------
@router.post("/login_auth2", response_model=TokenResponse)
async def login_auth2(form_data: OAuth2PasswordRequestForm = Depends()):
    email = _normalize_email(form_data.username)
    await detect_input_type(email)

    user = await User.get_or_none(email=email)

    if not user or not user.verify_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return _build_auth_response(user)


# ------------------------
# LOGIN WITH OTP SUPPORT
# ------------------------
@router.post("/login", description="""
    ### 👤 Dummy Users

    1.  Email: admin@gmail.com
        Password: admin

    2.  Email: staff@gmail.com
        Password: staff

    3.  Email: user1@gmail.com
        Password: user
             
    4.  Email: user2@gmail.com
        Password: user

""")
async def login(
    email: str = Form(...),
    password: str = Form(...)
):
    email = _normalize_email(email)
    await detect_input_type(email)

    user = await User.get_or_none(email=email)
    if not user or not user.verify_password(password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")

    return _build_auth_response(user)


# ------------------------
# SEND OTP
# ------------------------
@router.post("/send_otp", description="""
    ### 👤 Dummy Users

    1.  Email: admin@gmail.com
        Password: admin

    2.  Email: staff@gmail.com
        Password: staff

    3.  Email: user1@gmail.com
        Password: user
             
    4.  Email: user2@gmail.com
        Password: user

""")
async def send_otp(
    email: str = Form(...),
    purpose: str = Form("signup", description="Purpose of OTP: signup, forgot_password, login, change_gmail"),
):
    email = _normalize_email(email)
    await detect_input_type(email)
    purpose = purpose.strip().lower()

    user = await User.get_or_none(email=email)

    allowed_purposes = {"signup", "forgot_password", "login", "change_gmail"}
    if purpose not in allowed_purposes:
        raise HTTPException(status_code=400, detail="Invalid OTP purpose")

    if purpose == "signup" and user:
        raise HTTPException(status_code=400, detail="Email already registered")

    if purpose in {"forgot_password", "login"} and not user:
        raise HTTPException(status_code=400, detail="User not found")

    if purpose == "login" and user and getattr(user, "is_active_2fa", False):
        raise HTTPException(status_code=400, detail="OTP login is not enabled for this user")

    otp = await generate_otp(email, purpose)

    return {
        "status": "success",
        "message": f"OTP sent to {email} { '(DEBUG MODE: OTP is ' + otp + ')' if settings.DEBUG else '' }",
        "purpose": purpose,
    }


# ------------------------
# SIGNUP
# ------------------------
@router.post("/signup")
async def signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    otp: str = Form(...),
):
    email = _normalize_email(email)
    await detect_input_type(email)

    username = username.strip()
    password = password.strip()

    await verify_otp(email, otp, 'signup')

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")

    if await User.get_or_none(email=email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = await User.create(
        username=username,
        email=email,
        password=User.set_password(password)
    )

    return _build_auth_response(user, message="User created successfully")


@router.post("/google", response_model=dict)
async def google_auth(payload: SocialAuthRequest):
    profile = await verify_google_id_token(payload.id_token)

    if not profile.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account did not provide an email address.",
        )
    if not profile.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google email is not verified.",
        )

    user, created = await get_or_create_social_user(profile)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")

    message = "User created successfully" if created else "Login successful"
    return _build_auth_response(user, message=message)


@router.post("/apple", response_model=dict)
async def apple_auth(payload: AppleAuthRequest):
    profile = await verify_apple_id_token(
        payload.id_token,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )

    existing_user = await User.get_or_none(apple_id=profile.provider_user_id)
    if existing_user is None and not profile.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apple account email is required on first sign in.",
        )

    user, created = await get_or_create_social_user(profile)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")

    message = "User created successfully" if created else "Login successful"
    return _build_auth_response(user, message=message)






# ------------------------
# VERIFY OTP
# ------------------------
@router.post("/verify_otp")
async def verify_otp_route(
    email: str = Form(...),
    otp_value: str = Form(...),
    purpose: str = Form(...),
):
    email = _normalize_email(email)
    await detect_input_type(email)
    session_key = await verify_otp(email, otp_value, purpose)

    return {
        "status": "success",
        "sessionKey": session_key,
    }


# ------------------------
# RESET PASSWORD (LOGGED IN)
# ------------------------
@router.post("/reset_password")
async def reset_password(
    user: User = Depends(get_current_user),
    old_password: str = Form(...),
    new_password: str = Form(...),
):
    new_password = new_password.strip()
    if not user.verify_password(old_password):
        raise HTTPException(status_code=400, detail="Invalid old password")
    if not new_password:
        raise HTTPException(status_code=400, detail="New password is required")
    if old_password == new_password:
        raise HTTPException(status_code=400, detail="New password must be different from old password")

    user.password = User.set_password(new_password)
    await user.save()

    return {"message": "Password updated successfully"}


# ------------------------
# FORGOT PASSWORD
# ------------------------
@router.post("/forgot_password")
async def forgot_password(
    email: str = Form(...),
    password: str = Form(...),
    session_key: str = Form(...),
):
    email = _normalize_email(email)
    await detect_input_type(email)
    password = password.strip()
    session_key = session_key.strip()

    user = await User.get_or_none(email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not password:
        raise HTTPException(status_code=400, detail="Password is required")

    await verify_session_key(email, session_key, "forgot_password")

    user.password = User.set_password(password)
    await user.save()

    return {"message": "Password reset successfully"}


# ------------------------
# VERIFY TOKEN
# ------------------------
@router.get("/verify-token")
async def verify_token(request: Request, user: User = Depends(get_current_user)):
    response = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "auth_provider": user.auth_provider,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "photo": user.photo,
    }
    if hasattr(request.state, "new_tokens"):
        response["new_tokens"] = request.state.new_tokens
    return response
