# RoadWatch – developed by M K Rathish and team
# IIT Madras CoERS Road Safety Hackathon 2026
# All rights reserved.

"""Auth router — upgraded with role-based login + contractor creation (admin only)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.models import User
from app.schemas.schemas import (UserRegister, UserLogin, TokenResponse, UserOut,
    ContractorCreate, UserRoleUpdate, UserStatusUpdate)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Public: citizen registration only ─────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if not payload.email and not payload.phone:
        raise HTTPException(400, "Email or phone required")
    if payload.email and db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")
    if payload.phone and db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(400, "Phone already registered")
    # Public signup ONLY creates citizens — ignore any role override
    user = User(
        full_name=payload.full_name, phone=payload.phone, email=payload.email,
        password_hash=hash_password(payload.password),
        role="citizen",   # HARDCODED — no privilege escalation via public API
        country_id=payload.country_id, district_id=payload.district_id,
        is_verified=True, is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user_id=user.id, role=user.role, full_name=user.full_name)


# ── Login — returns role for client-side routing ──────────────
@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = None
    if payload.email:
        user = db.query(User).filter(User.email == payload.email).first()
    elif payload.phone:
        user = db.query(User).filter(User.phone == payload.phone).first()
    if not user or not verify_password(payload.password, user.password_hash or ""):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")
    user.last_login = datetime.utcnow()
    db.commit()
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user_id=user.id, role=user.role, full_name=user.full_name)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ── Admin only: create contractor account ─────────────────────
@router.post("/create-contractor", response_model=UserOut, status_code=201)
def create_contractor(
    payload: ContractorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(403, "Only admins can create contractor accounts")
    if payload.email and db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")
    if payload.phone and db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(400, "Phone already registered")
    user = User(
        full_name=payload.full_name, phone=payload.phone, email=payload.email,
        password_hash=hash_password(payload.password),
        role="contractor",
        contractor_company=payload.contractor_company,
        district_id=payload.district_id,
        is_verified=True, is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
