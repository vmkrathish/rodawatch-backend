# RoadWatch – developed by M K Rathish and team
# IIT Madras CoERS Road Safety Hackathon 2026
# All rights reserved.

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.core.database import get_db
from app.models.models import Road, Complaint, RoadProject, RoadRating
from app.schemas.schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStats)
def get_stats(district_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
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

    return DashboardStats(
        total_roads=total_roads,
        total_complaints=total_complaints,
        open_complaints=open_complaints,
        resolved_complaints=resolved_complaints,
        total_projects=total_projects,
        ongoing_projects=ongoing_projects,
        avg_quality_score=float(avg_score) if avg_score else None,
        total_budget_sanctioned=float(budget_sanctioned) if budget_sanctioned else None,
        total_budget_spent=float(budget_spent) if budget_spent else None,
    )

@router.get("/top-issues")
def top_issues(limit: int = 5, db: Session = Depends(get_db)):
    results = db.query(
        Complaint.issue_type,
        func.count(Complaint.id).label("count")
    ).group_by(Complaint.issue_type).order_by(func.count(Complaint.id).desc()).limit(limit).all()
    return [{"issue_type": r[0], "count": r[1]} for r in results]

@router.get("/worst-roads")
def worst_roads(limit: int = 5, district_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Road).filter(Road.is_active == True, Road.quality_score != None)
    if district_id:
        q = q.filter(Road.district_id == district_id)
    roads = q.order_by(Road.quality_score.asc()).limit(limit).all()
    return [{"id": r.id, "name": r.name, "road_number": r.road_number, "quality_score": r.quality_score} for r in roads]
