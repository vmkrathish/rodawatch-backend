# RoadWatch – developed by M K Rathish and team
# IIT Madras CoERS Road Safety Hackathon 2026
# All rights reserved.

"""
FIXES:
1. /near route placed BEFORE /{complaint_id} — avoids "near" being parsed as int (422 error).
2. lng_delta now uses math.cos() directly — removed the broken import_cos() helper
   that was being called inside a SQLAlchemy .between() filter expression.
"""
import os, uuid, math, json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from app.core.database import get_db
from app.core.security import get_current_user, get_optional_user
from app.core.config import settings
from app.models.models import Complaint, ComplaintMedia, Road, ExecutiveEngineer, User
from app.schemas.schemas import ComplaintCreate, ComplaintOut, ComplaintStatusUpdate
from app.services.yolo_service import analyze_image

router = APIRouter(prefix="/complaints", tags=["Complaints"])
UPLOAD_DIR = settings.UPLOAD_DIR


def _generate_ref_no(db: Session) -> str:
    year = datetime.utcnow().year
    count = db.query(Complaint).count() + 1
    return f"RW-{year}-{str(count).zfill(6)}"


def _auto_assign_ee(road: Optional[Road], db: Session) -> Optional[int]:
    if not road:
        return None
    ee = db.query(ExecutiveEngineer).filter(
        ExecutiveEngineer.district_id == road.district_id,
        ExecutiveEngineer.road_type_id == road.road_type_id,
        ExecutiveEngineer.is_active == True,
    ).first()
    if not ee:
        ee = db.query(ExecutiveEngineer).filter(
            ExecutiveEngineer.district_id == road.district_id,
            ExecutiveEngineer.is_active == True,
        ).first()
    return ee.id if ee else None


# FIX 1: /near BEFORE /{complaint_id}
@router.get("/near")
def complaints_near(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_km: float = Query(5.0),
    db: Session = Depends(get_db),
):
    """Complaints within approximate bounding box radius (no PostGIS required)."""
    lat_delta = radius_km / 111.0
    # FIX 2: math.cos() used directly — not inside SQLAlchemy filter
    lng_delta = radius_km / (111.0 * abs(math.cos(math.radians(lat))))
    return (
        db.query(Complaint)
        .filter(
            Complaint.latitude.between(lat - lat_delta, lat + lat_delta),
            Complaint.longitude.between(lng - lng_delta, lng + lng_delta),
        )
        .order_by(Complaint.submitted_at.desc())
        .limit(50)
        .all()
    )


@router.post("/", response_model=ComplaintOut, status_code=201)
def create_complaint(
    payload: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    road = db.query(Road).filter(Road.id == payload.road_id).first() if payload.road_id else None
    ee_id = _auto_assign_ee(road, db)
    ref_no = _generate_ref_no(db)

    complaint = Complaint(
        user_id=current_user.id if current_user else None,
        road_id=payload.road_id, ee_id=ee_id,
        complaint_ref_no=ref_no, issue_type=payload.issue_type,
        description=payload.description, latitude=payload.latitude,
        longitude=payload.longitude, location_text=payload.location_text,
        severity=payload.severity, status="Submitted",
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return (
        db.query(Complaint)
        .options(joinedload(Complaint.road), joinedload(Complaint.ee), joinedload(Complaint.media))
        .filter(Complaint.id == complaint.id)
        .first()
    )


@router.post("/{complaint_id}/upload-media")
async def upload_media(complaint_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")

    os.makedirs(f"{UPLOAD_DIR}/complaints", exist_ok=True)
    ext = os.path.splitext(file.filename or "file.jpg")[1]
    fname = f"{complaint.complaint_ref_no}_{uuid.uuid4().hex[:8]}{ext}"
    fpath = f"{UPLOAD_DIR}/complaints/{fname}"
    with open(fpath, "wb") as f:
        f.write(await file.read())

    yolo_result = None
    media_type = "image"
    if ext.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
        yolo_result = analyze_image(fpath)
        if yolo_result and yolo_result.get("detections"):
            complaint.yolo_detected_issues = yolo_result
            complaint.ai_severity_score = yolo_result.get("ai_severity_score", 5.0)
            detected = yolo_result.get("issue_type", "Other")
            if detected != "Other":
                complaint.issue_type = detected
    elif ext.lower() in [".mp4", ".mov", ".avi"]:
        media_type = "video"

    db.add(ComplaintMedia(complaint_id=complaint_id, file_path=f"/uploads/complaints/{fname}",
        media_type=media_type, yolo_result=yolo_result))
    db.commit()
    return {"message": "Media uploaded", "file_path": fpath, "yolo_result": yolo_result}


@router.get("/", response_model=List[ComplaintOut])
def list_complaints(
    status: Optional[str] = Query(None), severity: Optional[str] = Query(None),
    issue_type: Optional[str] = Query(None), district_id: Optional[int] = Query(None),
    skip: int = 0, limit: int = 30, db: Session = Depends(get_db),
):
    q = db.query(Complaint).options(
        joinedload(Complaint.road), joinedload(Complaint.ee), joinedload(Complaint.media))
    if status:
        q = q.filter(Complaint.status == status)
    if severity:
        q = q.filter(Complaint.severity == severity)
    if issue_type:
        q = q.filter(Complaint.issue_type == issue_type)
    if district_id:
        q = q.join(Road).filter(Road.district_id == district_id)
    return q.order_by(Complaint.submitted_at.desc()).offset(skip).limit(limit).all()


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    c = db.query(Complaint).options(
        joinedload(Complaint.road), joinedload(Complaint.ee), joinedload(Complaint.media)
    ).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(404, "Complaint not found")
    return c


@router.patch("/{complaint_id}/status")
def update_status(
    complaint_id: int, payload: ComplaintStatusUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["officer", "admin"]:
        raise HTTPException(403, "Only officers/admins can update complaint status")
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    complaint.status = payload.status
    if payload.resolution_notes:
        complaint.resolution_notes = payload.resolution_notes
    if payload.status == "Acknowledged" and not complaint.acknowledged_at:
        complaint.acknowledged_at = datetime.utcnow()
    if payload.status == "Resolved" and not complaint.resolved_at:
        complaint.resolved_at = datetime.utcnow()
    db.commit()
    return {"message": "Status updated", "status": payload.status}
