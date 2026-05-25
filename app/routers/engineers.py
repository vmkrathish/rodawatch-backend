from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from app.core.database import get_db
from app.models.models import ExecutiveEngineer
from app.schemas.schemas import ExecutiveEngineerOut

router = APIRouter(prefix="/engineers", tags=["Executive Engineers"])

@router.get("/", response_model=List[ExecutiveEngineerOut])
def list_engineers(
    district_id: Optional[int] = Query(None),
    road_type_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(ExecutiveEngineer).filter(ExecutiveEngineer.is_active == True)
    if district_id:
        q = q.filter(ExecutiveEngineer.district_id == district_id)
    if road_type_id:
        q = q.filter(ExecutiveEngineer.road_type_id == road_type_id)
    return q.all()

@router.get("/route")
def route_complaint(
    district_id: int = Query(...),
    road_type_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Given district + road type, return the correct EE to route a complaint to."""
    ee = db.query(ExecutiveEngineer).filter(
        ExecutiveEngineer.district_id == district_id,
        ExecutiveEngineer.is_active == True,
    )
    if road_type_id:
        specific = ee.filter(ExecutiveEngineer.road_type_id == road_type_id).first()
        if specific:
            return specific
    fallback = ee.first()
    if not fallback:
        return {"message": "No engineer found for this district"}
    return fallback
