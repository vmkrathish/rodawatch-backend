from pydantic import BaseModel, field_validator
from typing import Optional, List, Any
from datetime import date, datetime
from decimal import Decimal

# ── Auth ──────────────────────────────────────────────────────
class UserRegister(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    password: str
    role: Optional[str] = "citizen"   # public signup only allows citizen
    country_id: Optional[int] = None
    district_id: Optional[int] = None

class ContractorCreate(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    password: str
    contractor_company: str
    district_id: Optional[int] = None
    is_active: bool = True

class UserLogin(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str
    full_name: str

class UserOut(BaseModel):
    id: int
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    role: str
    contractor_company: Optional[str] = None
    district_id: Optional[int] = None
    is_verified: bool
    is_active: bool
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class UserRoleUpdate(BaseModel):
    role: str

class UserStatusUpdate(BaseModel):
    is_active: bool

# ── Reference ─────────────────────────────────────────────────
class RoadTypeOut(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    authority: Optional[str] = None
    class Config:
        from_attributes = True

class ContractorOut(BaseModel):
    id: int
    name: str
    registration_no: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool = True
    class Config:
        from_attributes = True

class ExecutiveEngineerOut(BaseModel):
    id: int
    name: str
    designation: str
    department: str
    phone: Optional[str] = None
    email: Optional[str] = None
    office_address: Optional[str] = None
    class Config:
        from_attributes = True

class CountryOut(BaseModel):
    id: int
    code: str
    name: str
    currency_code: str
    class Config:
        from_attributes = True

class StateOut(BaseModel):
    id: int
    code: str
    name: str
    class Config:
        from_attributes = True

class DistrictOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

# ── Roads ─────────────────────────────────────────────────────
class RoadCreate(BaseModel):
    district_id: int
    road_type_id: int
    road_number: Optional[str] = None
    name: str
    from_location: str
    to_location: str
    length_km: Optional[float] = None
    width_m: Optional[float] = None
    surface_type: str = "Unknown"
    last_relayed_date: Optional[date] = None
    current_contractor_id: Optional[int] = None
    ee_id: Optional[int] = None
    latitude_start: Optional[float] = None
    longitude_start: Optional[float] = None
    latitude_end: Optional[float] = None
    longitude_end: Optional[float] = None
    quality_score: Optional[int] = None

class RoadOut(BaseModel):
    id: int
    road_number: Optional[str] = None
    name: str
    from_location: str
    to_location: str
    length_km: Optional[Decimal] = None
    width_m: Optional[Decimal] = None
    surface_type: str
    last_relayed_date: Optional[date] = None
    quality_score: Optional[int] = None
    latitude_start: Optional[Decimal] = None
    longitude_start: Optional[Decimal] = None
    latitude_end: Optional[Decimal] = None
    longitude_end: Optional[Decimal] = None
    road_type: Optional[RoadTypeOut] = None
    current_contractor: Optional[ContractorOut] = None
    ee: Optional[ExecutiveEngineerOut] = None
    class Config:
        from_attributes = True

class RoadListItem(BaseModel):
    id: int
    road_number: Optional[str] = None
    name: str
    from_location: str
    to_location: str
    quality_score: Optional[int] = None
    last_relayed_date: Optional[date] = None
    surface_type: str
    class Config:
        from_attributes = True

class ProjectOut(BaseModel):
    id: int
    project_name: str
    project_type: str
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    status: str
    amount_sanctioned: Optional[Decimal] = None
    amount_spent: Optional[Decimal] = None
    currency_code: str
    fund_source: Optional[str] = None
    tender_no: Optional[str] = None
    contractor: Optional[ContractorOut] = None
    class Config:
        from_attributes = True

class MaintenanceOut(BaseModel):
    id: int
    scheduled_date: date
    maintenance_type: str
    description: Optional[str] = None
    status: str
    completed_date: Optional[date] = None
    class Config:
        from_attributes = True

# ── Complaints ────────────────────────────────────────────────
class ComplaintCreate(BaseModel):
    road_id: Optional[int] = None
    issue_type: str = "Other"
    description: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_text: Optional[str] = None
    severity: str = "Medium"

class ComplaintStatusUpdate(BaseModel):
    status: str
    resolution_notes: Optional[str] = None

class ComplaintMediaOut(BaseModel):
    id: int
    file_path: str
    media_type: str
    yolo_result: Optional[Any] = None
    class Config:
        from_attributes = True

class ComplaintOut(BaseModel):
    id: int
    complaint_ref_no: str
    issue_type: str
    description: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    location_text: Optional[str] = None
    severity: str
    status: str
    yolo_detected_issues: Optional[Any] = None
    ai_severity_score: Optional[Decimal] = None
    submitted_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    road: Optional[RoadListItem] = None
    ee: Optional[ExecutiveEngineerOut] = None
    media: List[ComplaintMediaOut] = []
    class Config:
        from_attributes = True

# ── Ratings ───────────────────────────────────────────────────
class RatingCreate(BaseModel):
    road_id: int
    rating: int
    comment: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v

class RatingOut(BaseModel):
    id: int
    road_id: int
    rating: int
    comment: Optional[str] = None
    rated_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# ── Offline Sync ──────────────────────────────────────────────
class OfflineSyncCreate(BaseModel):
    device_id: str
    action_type: str
    payload_json: str

# ── Dashboard ─────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_roads: int
    total_complaints: int
    open_complaints: int
    resolved_complaints: int
    total_projects: int
    ongoing_projects: int
    avg_quality_score: Optional[float] = None
    total_budget_sanctioned: Optional[float] = None
    total_budget_spent: Optional[float] = None
    total_users: Optional[int] = None
    total_contractors: Optional[int] = None
