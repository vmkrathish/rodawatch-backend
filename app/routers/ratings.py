from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.core.security import get_optional_user
from app.models.models import RoadRating, Road, User
from app.schemas.schemas import RatingCreate, RatingOut

router = APIRouter(prefix="/ratings", tags=["Ratings"])

@router.post("/", response_model=RatingOut, status_code=201)
def submit_rating(
    payload: RatingCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    road = db.query(Road).filter(Road.id == payload.road_id).first()
    if not road:
        raise HTTPException(404, "Road not found")

    rating = RoadRating(
        road_id=payload.road_id,
        user_id=current_user.id if current_user else None,
        rating=payload.rating,
        comment=payload.comment,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    db.add(rating)
    db.commit()

    # Recalculate quality score from average ratings
    from sqlalchemy import func
    avg = db.query(func.avg(RoadRating.rating)).filter(RoadRating.road_id == payload.road_id).scalar()
    if avg:
        road.quality_score = int((avg / 5.0) * 100)
        db.commit()

    db.refresh(rating)
    return rating


@router.get("/road/{road_id}", response_model=List[RatingOut])
def get_road_ratings(road_id: int, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(RoadRating).filter(RoadRating.road_id == road_id).order_by(
        RoadRating.rated_at.desc()
    ).offset(skip).limit(limit).all()
