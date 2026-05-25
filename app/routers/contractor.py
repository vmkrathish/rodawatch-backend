"""Contractor router — assigned projects and complaint handling."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, Road, Complaint, RoadProject, Contractor

router = APIRouter(prefix="/contractor", tags=["Contractor"])


def _require_contractor_or_admin(current_user: User):
    if current_user.role not in ["contractor", "admin"]:
        raise HTTPException(403, "Contractor access required")


@router.get("/my-roads")
def my_roads(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_contractor_or_admin(current_user)
    company = current_user.contractor_company
    if not company:
        return []
    contractor = db.query(Contractor).filter(Contractor.name.ilike(f"%{company}%")).first()
    if not contractor:
        return []
    roads = db.query(Road).options(
        joinedload(Road.road_type), joinedload(Road.district)
    ).filter(Road.current_contractor_id == contractor.id, Road.is_active == True).all()
    return [{
        "id": r.id, "road_number": r.road_number, "name": r.name,
        "from_location": r.from_location, "to_location": r.to_location,
        "surface_type": r.surface_type, "quality_score": r.quality_score,
        "road_type": r.road_type.name if r.road_type else None,
        "district": r.district.name if r.district else None,
    } for r in roads]


@router.get("/my-projects")
def my_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_contractor_or_admin(current_user)
    company = current_user.contractor_company
    if not company:
        return []
    contractor = db.query(Contractor).filter(Contractor.name.ilike(f"%{company}%")).first()
    if not contractor:
        return []
    projects = db.query(RoadProject).options(
        joinedload(RoadProject.road)
    ).filter(RoadProject.contractor_id == contractor.id).order_by(RoadProject.created_at.desc()).all()
    return [{
        "id": p.id, "project_name": p.project_name, "project_type": p.project_type,
        "status": p.status,
        "start_date": str(p.start_date) if p.start_date else None,
        "expected_end_date": str(p.expected_end_date) if p.expected_end_date else None,
        "amount_sanctioned": float(p.amount_sanctioned) if p.amount_sanctioned else None,
        "amount_spent": float(p.amount_spent) if p.amount_spent else None,
        "road_name": p.road.name if p.road else None,
        "road_id": p.road_id,
    } for p in projects]


@router.get("/my-complaints")
def my_complaints(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Complaints on roads assigned to this contractor."""
    _require_contractor_or_admin(current_user)
    company = current_user.contractor_company
    if not company:
        return []
    contractor = db.query(Contractor).filter(Contractor.name.ilike(f"%{company}%")).first()
    if not contractor:
        return []
    complaints = db.query(Complaint).options(
        joinedload(Complaint.road), joinedload(Complaint.media)
    ).join(Road, Complaint.road_id == Road.id, isouter=True)\
     .filter(Road.current_contractor_id == contractor.id)\
     .order_by(Complaint.submitted_at.desc()).limit(50).all()
    return [{
        "id": c.id, "complaint_ref_no": c.complaint_ref_no,
        "issue_type": c.issue_type, "description": c.description,
        "severity": c.severity, "status": c.status,
        "location_text": c.location_text,
        "submitted_at": str(c.submitted_at) if c.submitted_at else None,
        "road_name": c.road.name if c.road else None,
        "media_count": len(c.media),
    } for c in complaints]


@router.patch("/complaints/{complaint_id}/status")
def update_repair_status(
    complaint_id: int,
    status: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_contractor_or_admin(current_user)
    if status not in ["In Progress", "Resolved"]:
        raise HTTPException(400, "Contractors can only set: In Progress, Resolved")
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    complaint.status = status
    if notes:
        complaint.resolution_notes = notes
    from datetime import datetime
    if status == "Resolved":
        complaint.resolved_at = datetime.utcnow()
    db.commit()
    return {"message": "Status updated", "status": status}
