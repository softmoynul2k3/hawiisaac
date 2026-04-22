from fastapi import Depends, Header, HTTPException, Request, status
from .token import get_current_user, oauth2_scheme
from applications.user.models import User

async def superuser_required(current_user: User = Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required")
    return current_user


async def staff_required(current_user: User = Depends(get_current_user)):
    if current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Staff access required")
    return current_user


async def login_required(current_user: User = Depends(get_current_user)):
    return current_user


async def get_user_or_none(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    refresh_token: str | None = Header(default=None, alias="refresh-token"),
) -> User | None:
    try:
        current_user = await get_current_user(
            request=request,
            token=token,
            refresh_token=refresh_token,
        )
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return None
        raise

    if current_user is None:
        return None
    return current_user


def permission_required(codename: str):
    async def wrapper(current_user: User = Depends(get_current_user)):
        allowed = await current_user.has_permission(codename)

        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="Permission denied."
            )
        return current_user
    return wrapper

