from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from tortoise.transactions import in_transaction

from app.auth import login_required
from app.utils.file_manager import delete_file, update_file
from app.utils.otp_manager import verify_otp
from applications.user.models import  Group, Permission, User
from applications.user.schema import  serialize_user

router = APIRouter(tags=["User"])


async def _allowed(current_user: User, target_user: Optional[User], action: str) -> bool:
    is_self = target_user is not None and current_user.id == target_user.id

    if action == "view":
        if is_self:
            return True
        return (
            current_user.is_superuser
            or await current_user.has_permission("view_user")
        )

    if action == "update":
        if is_self:
            return True
        return (
            current_user.is_superuser
            or await current_user.has_permission("update_user")
        )

    if action == "delete":
        if is_self:
            return False
        return (
            current_user.is_superuser
            or await current_user.has_permission("delete_user")
        )

    if action == "list":
        return (
            current_user.is_superuser
            or await current_user.has_permission("view_user")
        )

    return False



@router.get("/users")
async def get_all_users(current_user: User = Depends(login_required)):
    if not await _allowed(current_user, None, "list"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    users = await User.all().order_by("-created_at").prefetch_related(
        "groups",
        "groups__permissions",
        "user_permissions",
    )
    return [await serialize_user(user) for user in users]


@router.get("/users/me")
async def get_me(current_user: User = Depends(login_required)):
    return await serialize_user(current_user)


@router.get("/users/{user_id}")
async def get_user(user_id: UUID, current_user: User = Depends(login_required)):
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not await _allowed(current_user, user, "view"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    return await serialize_user(user)


@router.put("/users/{user_id}", response_model=dict, dependencies=[Depends(login_required)])
async def update_user(
    user_id: UUID,
    otp: Optional[str] = None,
    username: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    dob: Optional[date] = Form(None),
    is_active: Optional[bool] = Form(None),
    is_superuser: Optional[bool] = Form(None),
    is_staff: Optional[bool] = Form(None),
    is_active_2fa: Optional[bool] = Form(None),
    group_ids: Optional[List[int]] = Form(None),
    permission_ids: Optional[List[int]] = Form(None),
    photo: Optional[UploadFile] = File(None),
    current_user: User = Depends(login_required),
):
    async with in_transaction() as connection:
        user = await User.get_or_none(id=user_id).using_db(connection).prefetch_related("groups", "user_permissions")
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        has_update_permission = await _allowed(current_user, user, "update")

        if not has_update_permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission to update this user.")

        if user.is_superuser and not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update a superuser account.")

        sensitive_fields_changed = any(
            value is not None
            for value in (
                is_active,
                is_superuser,
                is_staff,
                group_ids,
                permission_ids,
            )
        )
        can_manage_other_users = (
            current_user.is_superuser
            or await current_user.has_permission("update_user")
        )
        if sensitive_fields_changed and not can_manage_other_users:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update sensitive fields.")

        if username is not None:
            cleaned_username = username.strip()
            user.username = cleaned_username or None
            if cleaned_username:
                username_exists = (
                    await User.filter(username=cleaned_username)
                    .exclude(id=user.id)
                    .using_db(connection)
                    .exists()
                )
                if username_exists:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already in use.",
                    )

        if email is not None:
            cleaned_email = email.strip()
            user.email = cleaned_email or None
            if cleaned_email:
                email_exists = await User.filter(email=cleaned_email).exclude(id=user.id).using_db(connection).exists()
                if email_exists:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use.")
                else:
                    if not otp:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP required for changing gmail.")
                    else:
                        await verify_otp(cleaned_email, otp, 'change_gmail')

        if first_name is not None:
            cleaned_first_name = first_name.strip()
            user.first_name = cleaned_first_name or None

        if last_name is not None:
            cleaned_last_name = last_name.strip()
            user.last_name = cleaned_last_name or None

        if gender is not None:
            cleaned_gender = gender.strip()
            user.gender = cleaned_gender or None

        if dob is not None:
            user.dob = dob

        if is_active is not None:
            user.is_active = is_active

        if is_superuser is not None:
            if not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only superuser can modify superuser status.",
                )
            user.is_superuser = is_superuser

        if is_staff is not None:
            if not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only superuser can modify staff status.",
                )
            user.is_staff = is_staff

        if is_active_2fa is not None:
            if current_user.id != user.id and not can_manage_other_users:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not allowed to update 2FA status for this user.",
                )
            user.is_active_2fa = is_active_2fa

        if photo is not None and photo.filename:
            user.photo = await update_file(
                photo,
                user.photo,
                upload_to="user_photo",
                allowed_extensions=["jpg", "png", "jpeg", "webp"],
            )

        await user.save(using_db=connection)

        if group_ids is not None:
            unique_group_ids = list(dict.fromkeys(group_ids))
            groups = await Group.filter(id__in=unique_group_ids).using_db(connection)
            found_group_ids = {group.id for group in groups}
            missing_group_ids = [group_id for group_id in unique_group_ids if group_id not in found_group_ids]
            if missing_group_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "Some groups were not found", "missing_group_ids": missing_group_ids},
                )

            await user.groups.clear()
            if groups:
                await user.groups.add(*groups)

        if permission_ids is not None:
            unique_permission_ids = list(dict.fromkeys(permission_ids))
            permissions = await Permission.filter(id__in=unique_permission_ids).using_db(connection)
            found_permission_ids = {permission.id for permission in permissions}
            missing_permission_ids = [
                permission_id for permission_id in unique_permission_ids if permission_id not in found_permission_ids
            ]
            if missing_permission_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "Some permissions were not found", "missing_permission_ids": missing_permission_ids},
                )

            await user.user_permissions.clear()
            if permissions:
                await user.user_permissions.add(*permissions)

    updated_user = await User.get(id=user_id)
    return {"message": "User updated successfully", "user": await serialize_user(updated_user)}


@router.delete(
    "/users/{user_id}",
    dependencies=[
        Depends(login_required),
    ],
)
async def delete_user(user_id: UUID, current_user: User = Depends(login_required)):
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account.")

    if not await _allowed(current_user, user, "delete"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    if user.is_superuser and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete a superuser account.")

    if user.photo:
        await delete_file(user.photo)

    await user.delete()
    return {"detail": "User deleted successfully"}

