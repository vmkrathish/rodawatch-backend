from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from app.core.database import get_db
from app.core.security import get_optional_user, get_current_user
from app.models.models import RoadRating, Road, User
from app.schemas.schemas import RatingCreate, RatingOut

router = APIRouter(prefix="/ratings", tags=["Ratings"])


def _recalc_quality(road: Road, db: Session):
    """Recalculate road quality_score from average of all user ratings."""
    avg = db.query(func.avg(RoadRating.rating)).filter(
        RoadRating.road_id == road.id
    ).scalar()
    if avg is not None:
        road.quality_score = int((float(avg) / 5.0) * 100)
        db.commit()


@router.post("/", response_model=RatingOut, status_code=200)
def submit_or_update_rating(
    payload: RatingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),   # auth required to rate
):
    """
    Submit a rating for a road.
    - If the user has already rated this road → UPDATE the existing row.
    - If not → INSERT a new row.
    One rating per user per road — always.
    """
    road = db.query(Road).filter(Road.id == payload.road_id).first()
    if not road:
        raise HTTPException(404, "Road not found")

    # Check for existing rating by this user on this road
    existing = db.query(RoadRating).filter(
        RoadRating.road_id == payload.road_id,
        RoadRating.user_id == current_user.id,
    ).first()

    if existing:
        # UPDATE — edit previous rating
        existing.rating    = payload.rating
        existing.comment   = payload.comment
        existing.latitude  = payload.latitude
        existing.longitude = payload.longitude
        existing.rated_at  = func.now()   # refresh timestamp on edit
        db.commit()
        db.refresh(existing)
        _recalc_quality(road, db)
        return existing
    else:
        # INSERT — first time rating
        new_rating = RoadRating(
            road_id   = payload.road_id,
            user_id   = current_user.id,
            rating    = payload.rating,
            comment   = payload.comment,
            latitude  = payload.latitude,
            longitude = payload.longitude,
        )
        db.add(new_rating)
        db.commit()
        db.refresh(new_rating)
        _recalc_quality(road, db)
        return new_rating


@router.get("/my-rating/{road_id}", response_model=Optional[RatingOut])
def get_my_rating(
    road_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current user's existing rating for a road (or null if not rated yet)."""
    return db.query(RoadRating).filter(
        RoadRating.road_id == road_id,
        RoadRating.user_id == current_user.id,
    ).first()


@router.get("/road/{road_id}", response_model=List[RatingOut])
def get_road_ratings(
    road_id: int, skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
):
    """All ratings for a road, newest first."""
    return db.query(RoadRating).filter(
        RoadRating.road_id == road_id,
    ).order_by(RoadRating.rated_at.desc()).offset(skip).limit(limit).all()

