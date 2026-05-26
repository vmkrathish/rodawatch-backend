# RoadWatch – developed by M K Rathish and team
# IIT Madras CoERS Road Safety Hackathon 2026
# All rights reserved.

"""Profile router — view, update, image upload/delete for all roles."""
import os, uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user, hash_password, verify_password
from app.models.models import User
from app.core.config import settings

router = APIRouter(prefix="/profile", tags=["Profile"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    contractor_company: Optional[str] = None
    district_id: Optional[int] = None
    country_id: Optional[int] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


def _build_img_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return f"https://roadwatch-backend.onrender.com/{path.lstrip('/')}"


@router.get("/me")
def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "email": current_user.email,
        "role": current_user.role,
        "contractor_company": current_user.contractor_company,
        "profile_image": current_user.profile_image,
        "profile_image_url": _build_img_url(current_user.profile_image),
        "district_id": current_user.district_id,
        "country_id": current_user.country_id,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "last_login": str(current_user.last_login) if current_user.last_login else None,
        "created_at": str(current_user.created_at) if current_user.created_at else None,
    }


@router.put("/me")
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.phone and payload.phone != current_user.phone:
        if db.query(User).filter(User.phone == payload.phone, User.id != current_user.id).first():
            raise HTTPException(400, "Phone number already in use")
    if payload.email and payload.email != current_user.email:
        if db.query(User).filter(User.email == payload.email, User.id != current_user.id).first():
            raise HTTPException(400, "Email already in use")
    if payload.full_name:  current_user.full_name = payload.full_name
    if payload.phone is not None: current_user.phone = payload.phone
    if payload.email is not None: current_user.email = payload.email
    if payload.contractor_company is not None: current_user.contractor_company = payload.contractor_company
    if payload.district_id is not None: current_user.district_id = payload.district_id
    if payload.country_id is not None: current_user.country_id = payload.country_id
    db.commit()
    return {"message": "Profile updated successfully"}


@router.post("/upload-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload or replace profile picture."""
    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, "Only JPEG, PNG, WebP images are allowed")

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(400, "Image too large — maximum 5 MB allowed")

    # Delete old file from disk
    if current_user.profile_image:
        old_path = current_user.profile_image.lstrip("/")
        if os.path.exists(old_path):
            try: os.remove(old_path)
            except: pass

    ext = (file.filename or "img.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"): ext = "jpg"
    fname = f"profile_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    save_dir = os.path.join(settings.UPLOAD_DIR, "profiles")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, fname)

    with open(save_path, "wb") as f:
        f.write(content)

    relative_path = f"uploads/profiles/{fname}"
    current_user.profile_image = relative_path
    db.commit()

    return {
        "message": "Profile image uploaded successfully",
        "profile_image": relative_path,
        "profile_image_url": _build_img_url(relative_path),
    }


@router.delete("/remove-image")
def remove_profile_image(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove profile picture — deletes file from disk and clears DB field."""
    if not current_user.profile_image:
        raise HTTPException(400, "No profile image to remove")

    # Delete the physical file
    old_path = current_user.profile_image.lstrip("/")
    if os.path.exists(old_path):
        try:
            os.remove(old_path)
        except Exception:
            pass  # File may already be deleted; still clear the DB field

    current_user.profile_image = None
    db.commit()
    return {"message": "Profile image removed successfully"}


@router.post("/change-password")
def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash or ""):
        raise HTTPException(400, "Current password is incorrect")
    if len(payload.new_password) < 4:
        raise HTTPException(400, "Password must be at least 4 characters")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully"}
