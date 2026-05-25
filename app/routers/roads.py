# RoadWatch – developed by M K Rathish and team
# IIT Madras CoERS Road Safety Hackathon 2026
# All rights reserved.

"""FIX: /ref/* routes BEFORE /{road_id}. Added /ref/contractors endpoint."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from app.core.database import get_db
from app.models.models import Road, RoadType, District, StateRegion, Country, Contractor
from app.schemas.schemas import RoadOut, RoadListItem, RoadTypeOut, CountryOut, StateOut, DistrictOut, ContractorOut

router = APIRouter(prefix="/roads", tags=["Roads"])


# ── /ref/* routes FIRST (must be before /{road_id}) ──────────
@router.get("/ref/types", response_model=List[RoadTypeOut], tags=["Reference"])
def list_road_types(db: Session = Depends(get_db)):
    return db.query(RoadType).all()

@router.get("/ref/countries", response_model=List[CountryOut], tags=["Reference"])
def list_countries(db: Session = Depends(get_db)):
    return db.query(Country).all()

@router.get("/ref/states", response_model=List[StateOut], tags=["Reference"])
def list_states(country_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(StateRegion)
    if country_id:
        q = q.filter(StateRegion.country_id == country_id)
    return q.all()

@router.get("/ref/districts", response_model=List[DistrictOut], tags=["Reference"])
def list_districts(state_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(District)
    if state_id:
        q = q.filter(District.state_region_id == state_id)
    return q.all()

@router.get("/ref/contractors", response_model=List[ContractorOut], tags=["Reference"])
def list_contractors(is_active: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    """Returns contractor list for admin dropdowns (add road, assign contractor)."""
    q = db.query(Contractor)
    if is_active is not None:
        q = q.filter(Contractor.is_active == is_active)
    return q.order_by(Contractor.name).all()


# ── Collection ────────────────────────────────────────────────
@router.get("/", response_model=List[RoadOut])
def list_roads(
    district_id: Optional[int] = Query(None),
    road_type_id: Optional[int] = Query(None),
    quality_min: Optional[int] = Query(None),
    quality_max: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(Road).options(
        joinedload(Road.road_type),
        joinedload(Road.current_contractor),
        joinedload(Road.ee),
    ).filter(Road.is_active == True)
    if district_id:
        q = q.filter(Road.district_id == district_id)
    if road_type_id:
        q = q.filter(Road.road_type_id == road_type_id)
    if quality_min is not None:
        q = q.filter(Road.quality_score >= quality_min)
    if quality_max is not None:
        q = q.filter(Road.quality_score <= quality_max)
    if search:
        q = q.filter(Road.name.ilike(f"%{search}%") | Road.road_number.ilike(f"%{search}%"))
    return q.offset(skip).limit(limit).all()


# ── Individual road (AFTER /ref/* and /) ─────────────────────
@router.get("/{road_id}", response_model=RoadOut)
def get_road(road_id: int, db: Session = Depends(get_db)):
    road = db.query(Road).options(
        joinedload(Road.road_type),
        joinedload(Road.current_contractor),
        joinedload(Road.ee),
        joinedload(Road.projects),
        joinedload(Road.maintenance_schedules),
    ).filter(Road.id == road_id, Road.is_active == True).first()
    if not road:
        raise HTTPException(404, "Road not found")
    return road

@router.get("/{road_id}/projects")
def get_road_projects(road_id: int, db: Session = Depends(get_db)):
    from app.models.models import RoadProject
    road = db.query(Road).filter(Road.id == road_id).first()
    if not road:
        raise HTTPException(404, "Road not found")
    projects = db.query(RoadProject).options(
        joinedload(RoadProject.contractor)
    ).filter(RoadProject.road_id == road_id).all()
    return [
        {
            "id": p.id, "project_name": p.project_name, "project_type": p.project_type,
            "start_date": str(p.start_date) if p.start_date else None,
            "expected_end_date": str(p.expected_end_date) if p.expected_end_date else None,
            "actual_end_date": str(p.actual_end_date) if p.actual_end_date else None,
            "status": p.status,
            "amount_sanctioned": float(p.amount_sanctioned) if p.amount_sanctioned else None,
            "amount_spent": float(p.amount_spent) if p.amount_spent else None,
            "currency_code": p.currency_code, "fund_source": p.fund_source, "tender_no": p.tender_no,
            "contractor": {"id": p.contractor.id, "name": p.contractor.name} if p.contractor else None,
        }
        for p in projects
    ]

@router.get("/{road_id}/maintenance")
def get_road_maintenance(road_id: int, db: Session = Depends(get_db)):
    from app.models.models import MaintenanceSchedule
    schedules = db.query(MaintenanceSchedule).filter(
        MaintenanceSchedule.road_id == road_id
    ).order_by(MaintenanceSchedule.scheduled_date.desc()).all()
    return [
        {
            "id": s.id, "scheduled_date": str(s.scheduled_date),
            "maintenance_type": s.maintenance_type, "description": s.description,
            "status": s.status, "completed_date": str(s.completed_date) if s.completed_date else None,
        }
        for s in schedules
    ]
