"""Location Master CRUD — Countries, States, Districts (Admin only)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Country, StateRegion, District, User

router = APIRouter(prefix="/location", tags=["Location Master"])

# ── Schemas ───────────────────────────────────────────────────
class CountryIn(BaseModel):
    code: str
    name: str
    currency_code: str = "INR"

class StateIn(BaseModel):
    country_id: int
    code: str
    name: str

class DistrictIn(BaseModel):
    state_region_id: int
    name: str

def _admin(current_user: User):
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")

# ── Countries ────────────────────────────────────────────────
@router.get("/countries")
def list_countries(search: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Country)
    if search:
        q = q.filter(Country.name.ilike(f"%{search}%") | Country.code.ilike(f"%{search}%"))
    rows = q.order_by(Country.name).all()
    return [{"id": r.id, "code": r.code, "name": r.name, "currency_code": r.currency_code, "state_count": len(r.states)} for r in rows]

@router.post("/countries", status_code=201)
def create_country(payload: CountryIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    _admin(u)
    if db.query(Country).filter(Country.code == payload.code.upper()).first():
        raise HTTPException(400, f"Country code '{payload.code}' already exists")
    c = Country(code=payload.code.upper(), name=payload.name, currency_code=payload.currency_code.upper())
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "code": c.code, "name": c.name, "currency_code": c.currency_code}

@router.put("/countries/{cid}")
def update_country(cid: int, payload: CountryIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    _admin(u)
    c = db.query(Country).filter(Country.id == cid).first()
    if not c: raise HTTPException(404, "Country not found")
    c.code = payload.code.upper(); c.name = payload.name; c.currency_code = payload.currency_code.upper()
    db.commit()
    return {"id": c.id, "code": c.code, "name": c.name, "currency_code": c.currency_code}

@router.delete("/countries/{cid}")
def delete_country(cid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    _admin(u)
    c = db.query(Country).filter(Country.id == cid).first()
    if not c: raise HTTPException(404, "Country not found")
    if c.states: raise HTTPException(400, "Cannot delete — country has linked states")
    db.delete(c); db.commit()
    return {"message": "Country deleted"}

# ── States ────────────────────────────────────────────────────
@router.get("/states")
def list_states(country_id: Optional[int] = None, search: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(StateRegion)
    if country_id: q = q.filter(StateRegion.country_id == country_id)
    if search: q = q.filter(StateRegion.name.ilike(f"%{search}%"))
    rows = q.order_by(StateRegion.name).all()
    return [{"id": r.id, "code": r.code, "name": r.name, "country_id": r.country_id,
             "country_name": r.country.name if r.country else None,
             "district_count": len(r.districts)} for r in rows]

@router.post("/states", status_code=201)
def create_state(payload: StateIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    _admin(u)
    if not db.query(Country).filter(Country.id == payload.country_id).first():
        raise HTTPException(404, "Country not found")
    s = StateRegion(country_id=payload.country_id, code=payload.code.upper(), name=payload.name)
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id, "code": s.code, "name": s.name, "country_id": s.country_id}

@router.put("/states/{sid}")
def update_state(sid: int, payload: StateIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    _admin(u)
    s = db.query(StateRegion).filter(StateRegion.id == sid).first()
    if not s: raise HTTPException(404, "State not found")
    s.country_id = payload.country_id; s.code = payload.code.upper(); s.name = payload.name
    db.commit()
    return {"id": s.id, "code": s.code, "name": s.name}

@router.delete("/states/{sid}")
def delete_state(sid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    _admin(u)
    s = db.query(StateRegion).filter(StateRegion.id == sid).first()
    if not s: raise HTTPException(404, "State not found")
    if s.districts: raise HTTPException(400, "Cannot delete — state has linked districts")
    db.delete(s); db.commit()
    return {"message": "State deleted"}

# ── Districts ─────────────────────────────────────────────────
@router.get("/districts")
def list_districts(state_id: Optional[int] = None, search: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(District)
    if state_id: q = q.filter(District.state_region_id == state_id)
    if search: q = q.filter(District.name.ilike(f"%{search}%"))
    rows = q.order_by(District.name).all()
    return [{"id": r.id, "name": r.name, "state_region_id": r.state_region_id,
             "state_name": r.state_region.name if r.state_region else None,
             "road_count": len(r.roads)} for r in rows]

@router.post("/districts", status_code=201)
def create_district(payload: DistrictIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    _admin(u)
    if not db.query(StateRegion).filter(StateRegion.id == payload.state_region_id).first():
        raise HTTPException(404, "State not found")
    d = District(state_region_id=payload.state_region_id, name=payload.name)
    db.add(d); db.commit(); db.refresh(d)
    return {"id": d.id, "name": d.name, "state_region_id": d.state_region_id}

@router.put("/districts/{did}")
def update_district(did: int, payload: DistrictIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    _admin(u)
    d = db.query(District).filter(District.id == did).first()
    if not d: raise HTTPException(404, "District not found")
    d.state_region_id = payload.state_region_id; d.name = payload.name
    db.commit()
    return {"id": d.id, "name": d.name, "state_region_id": d.state_region_id}

@router.delete("/districts/{did}")
def delete_district(did: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    _admin(u)
    d = db.query(District).filter(District.id == did).first()
    if not d: raise HTTPException(404, "District not found")
    if d.roads: raise HTTPException(400, "Cannot delete — district has linked roads")
    db.delete(d); db.commit()
    return {"message": "District deleted"}
