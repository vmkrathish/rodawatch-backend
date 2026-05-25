import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.models.models import OfflineSyncQueue, Complaint, RoadRating
from app.schemas.schemas import OfflineSyncCreate

router = APIRouter(prefix="/sync", tags=["Offline Sync"])

@router.post("/queue")
def add_to_queue(payload: OfflineSyncCreate, db: Session = Depends(get_db)):
    item = OfflineSyncQueue(
        device_id=payload.device_id,
        action_type=payload.action_type,
        payload_json=payload.payload_json,
        status="pending",
    )
    db.add(item)
    db.commit()
    return {"message": "Queued for sync", "id": item.id}

@router.post("/process/{device_id}")
def process_queue(device_id: str, db: Session = Depends(get_db)):
    pending = db.query(OfflineSyncQueue).filter(
        OfflineSyncQueue.device_id == device_id,
        OfflineSyncQueue.status == "pending"
    ).all()

    processed = []
    for item in pending:
        try:
            payload = json.loads(item.payload_json)
            if item.action_type == "complaint":
                c = Complaint(**{k: v for k, v in payload.items() if k != "complaint_ref_no"})
                from app.routers.complaints import _generate_ref_no
                c.complaint_ref_no = _generate_ref_no(db)
                db.add(c)
                db.flush()
            elif item.action_type == "road_rating":
                r = RoadRating(**payload)
                db.add(r)
            item.status = "synced"
            item.synced_at = datetime.utcnow()
            processed.append(item.id)
        except Exception as e:
            item.status = "failed"
    db.commit()
    return {"processed": processed, "total": len(pending)}

@router.get("/status/{device_id}")
def sync_status(device_id: str, db: Session = Depends(get_db)):
    pending = db.query(OfflineSyncQueue).filter(
        OfflineSyncQueue.device_id == device_id, OfflineSyncQueue.status == "pending"
    ).count()
    return {"device_id": device_id, "pending_count": pending}
