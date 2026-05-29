# RoadWatch – developed by M K Rathish and team
# IIT Madras CoERS Road Safety Hackathon 2026
# All rights reserved.

"""Admin router — user management, road creation, analytics."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional, List
from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.models.models import User, Road, Complaint, RoadProject, RoadRating, District
from app.schemas.schemas import (UserOut, UserRoleUpdate, UserStatusUpdate,
    RoadCreate, RoadOut, DashboardStats)

router = APIRouter(prefix="/admin", tags=["Admin"])


def _require_admin(current_user: User):
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")


# ── User Management ───────────────────────────────────────────
@router.get("/users")          # FIX: removed response_model — returns plain dict so profile_image is never stripped
def list_users(
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if is_active is not None:
        q = q.filter(User.is_active == is_active)
    if search:
        q = q.filter(
            User.full_name.ilike(f"%{search}%") |
            User.email.ilike(f"%{search}%") |
            User.phone.ilike(f"%{search}%")
        )
    users = q.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    # Explicit dict — profile_image always included regardless of Pydantic schema version
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "phone": u.phone,
            "email": u.email,
            "role": u.role,
            "contractor_company": u.contractor_company,
            "district_id": u.district_id,
            "is_verified": u.is_verified,
            "is_active": u.is_active,
            "profile_image": u.profile_image,   # relative path e.g. "uploads/profiles/profile_2_abc.jpg"
            "created_at": str(u.created_at) if u.created_at else None,
        }
        for u in users
    ]


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_admin(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int, payload: UserRoleUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    if payload.role not in ["citizen", "contractor", "admin"]:
        raise HTTPException(400, "Invalid role. Use: citizen, contractor, admin")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.role = payload.role
    db.commit()
    return {"message": f"Role updated to {payload.role}", "user_id": user_id}


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: int, payload: UserStatusUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = payload.is_active
    db.commit()
    status_str = "activated" if payload.is_active else "deactivated"
    return {"message": f"User {status_str}", "user_id": user_id}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_admin(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == current_user.id:
        raise HTTPException(400, "Cannot delete your own account")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


# ── Road Management (admin adds roads via app) ────────────────
@router.post("/roads", response_model=RoadOut, status_code=201)
def create_road(
    payload: RoadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    road = Road(
        district_id=payload.district_id,
        road_type_id=payload.road_type_id,
        road_number=payload.road_number,
        name=payload.name,
        from_location=payload.from_location,
        to_location=payload.to_location,
        length_km=payload.length_km,
        width_m=payload.width_m,
        surface_type=payload.surface_type,
        last_relayed_date=payload.last_relayed_date,
        current_contractor_id=payload.current_contractor_id,
        ee_id=payload.ee_id,
        latitude_start=payload.latitude_start,
        longitude_start=payload.longitude_start,
        latitude_end=payload.latitude_end,
        longitude_end=payload.longitude_end,
        quality_score=payload.quality_score,
        is_active=True,
    )
    db.add(road)
    db.commit()
    db.refresh(road)
    return db.query(Road).options(
        joinedload(Road.road_type), joinedload(Road.current_contractor), joinedload(Road.ee)
    ).filter(Road.id == road.id).first()


@router.patch("/roads/{road_id}/contractor")
def assign_contractor(
    road_id: int,
    contractor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    road = db.query(Road).filter(Road.id == road_id).first()
    if not road:
        raise HTTPException(404, "Road not found")
    road.current_contractor_id = contractor_id
    db.commit()
    return {"message": "Contractor assigned", "road_id": road_id, "contractor_id": contractor_id}


# ── Analytics ─────────────────────────────────────────────────
@router.get("/analytics", response_model=DashboardStats)
def analytics(district_id: Optional[int] = Query(None), db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    _require_admin(current_user)

    rq = db.query(Road).filter(Road.is_active == True)
    cq = db.query(Complaint)
    pq = db.query(RoadProject)

    if district_id:
        rq = rq.filter(Road.district_id == district_id)
        cq = cq.join(Road).filter(Road.district_id == district_id)
        pq = pq.join(Road).filter(Road.district_id == district_id)

    total_roads = rq.count()
    total_complaints = cq.count()
    open_complaints = cq.filter(Complaint.status.in_(["Submitted","Acknowledged","In Progress"])).count()
    resolved_complaints = cq.filter(Complaint.status == "Resolved").count()
    total_projects = pq.count()
    ongoing_projects = pq.filter(RoadProject.status == "Ongoing").count()
    avg_score = rq.with_entities(func.avg(Road.quality_score)).scalar()
    budget_sanctioned = pq.with_entities(func.sum(RoadProject.amount_sanctioned)).scalar()
    budget_spent = pq.with_entities(func.sum(RoadProject.amount_spent)).scalar()
    total_users = db.query(User).count()
    total_contractors = db.query(User).filter(User.role == "contractor").count()

    return DashboardStats(
        total_roads=total_roads, total_complaints=total_complaints,
        open_complaints=open_complaints, resolved_complaints=resolved_complaints,
        total_projects=total_projects, ongoing_projects=ongoing_projects,
        avg_quality_score=float(avg_score) if avg_score else None,
        total_budget_sanctioned=float(budget_sanctioned) if budget_sanctioned else None,
        total_budget_spent=float(budget_spent) if budget_spent else None,
        total_users=total_users, total_contractors=total_contractors,
    )


@router.get("/analytics/district-issues")
def district_issues(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_admin(current_user)
    results = db.query(
        District.name,
        func.count(Complaint.id).label("complaint_count"),
    ).join(Road, Road.district_id == District.id, isouter=True)\
     .join(Complaint, Complaint.road_id == Road.id, isouter=True)\
     .group_by(District.id)\
     .all()
    return [{"district": r[0], "complaints": r[1] or 0} for r in results]


@router.get("/analytics/contractor-performance")
def contractor_performance(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_admin(current_user)
    from app.models.models import Contractor
    results = db.query(
        Contractor.name,
        func.count(RoadProject.id).label("project_count"),
        func.sum(RoadProject.amount_spent).label("total_spent"),
        func.count(Road.id).label("roads_assigned"),
    ).outerjoin(RoadProject, RoadProject.contractor_id == Contractor.id)\
     .outerjoin(Road, Road.current_contractor_id == Contractor.id)\
     .group_by(Contractor.id)\
     .all()
    return [{
        "contractor": r[0],
        "projects": r[1] or 0,
        "total_spent": float(r[2]) if r[2] else 0,
        "roads_assigned": r[3] or 0,
    } for r in results]
