# RoadWatch – developed by M K Rathish and team
# IIT Madras CoERS Road Safety Hackathon 2026
# All rights reserved.

from sqlalchemy import (Column, Integer, String, Text, Date, TIMESTAMP,
    Numeric, ForeignKey, SmallInteger, Boolean, JSON, func)
from sqlalchemy.orm import relationship
from app.core.database import Base

class Country(Base):
    __tablename__ = "countries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(3), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    currency_code = Column(String(3), nullable=False, default="INR")
    created_at = Column(TIMESTAMP, server_default=func.now())
    states = relationship("StateRegion", back_populates="country")
    users = relationship("User", back_populates="country")
    contractors = relationship("Contractor", back_populates="country")

class StateRegion(Base):
    __tablename__ = "states_regions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    country_id = Column(Integer, ForeignKey("countries.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(10), nullable=False)
    name = Column(String(150), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    country = relationship("Country", back_populates="states")
    districts = relationship("District", back_populates="state_region")

class District(Base):
    __tablename__ = "districts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    state_region_id = Column(Integer, ForeignKey("states_regions.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(150), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    state_region = relationship("StateRegion", back_populates="districts")
    roads = relationship("Road", back_populates="district")
    executive_engineers = relationship("ExecutiveEngineer", back_populates="district")
    users = relationship("User", back_populates="district")

class RoadType(Base):
    __tablename__ = "road_types"
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    authority = Column(String(150))
    roads = relationship("Road", back_populates="road_type")
    executive_engineers = relationship("ExecutiveEngineer", back_populates="road_type")

class Contractor(Base):
    __tablename__ = "contractors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    country_id = Column(Integer, ForeignKey("countries.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    registration_no = Column(String(100))
    contact_person = Column(String(150))
    phone = Column(String(30))
    email = Column(String(150))
    address = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    country = relationship("Country", back_populates="contractors")
    roads = relationship("Road", back_populates="current_contractor")
    projects = relationship("RoadProject", back_populates="contractor")

class ExecutiveEngineer(Base):
    __tablename__ = "executive_engineers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="CASCADE"), nullable=False)
    road_type_id = Column(SmallInteger, ForeignKey("road_types.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(150), nullable=False)
    designation = Column(String(150), nullable=False, default="Executive Engineer")
    department = Column(String(200), nullable=False)
    phone = Column(String(30))
    email = Column(String(150))
    office_address = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    district = relationship("District", back_populates="executive_engineers")
    road_type = relationship("RoadType", back_populates="executive_engineers")
    roads = relationship("Road", back_populates="ee")
    complaints = relationship("Complaint", back_populates="ee")

class Road(Base):
    __tablename__ = "roads"
    id = Column(Integer, primary_key=True, autoincrement=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="CASCADE"), nullable=False)
    road_type_id = Column(SmallInteger, ForeignKey("road_types.id", ondelete="RESTRICT"), nullable=False)
    road_number = Column(String(50))
    name = Column(String(255), nullable=False)
    from_location = Column(String(200), nullable=False)
    to_location = Column(String(200), nullable=False)
    length_km = Column(Numeric(8, 3))
    width_m = Column(Numeric(5, 2))
    surface_type = Column(String(20), default="Unknown")
    last_relayed_date = Column(Date)
    current_contractor_id = Column(Integer, ForeignKey("contractors.id", ondelete="SET NULL"), nullable=True)
    ee_id = Column(Integer, ForeignKey("executive_engineers.id", ondelete="SET NULL"), nullable=True)
    latitude_start = Column(Numeric(10, 7))
    longitude_start = Column(Numeric(10, 7))
    latitude_end = Column(Numeric(10, 7))
    longitude_end = Column(Numeric(10, 7))
    geojson_path = Column(Text)
    quality_score = Column(SmallInteger)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    district = relationship("District", back_populates="roads")
    road_type = relationship("RoadType", back_populates="roads")
    current_contractor = relationship("Contractor", back_populates="roads")
    ee = relationship("ExecutiveEngineer", back_populates="roads")
    projects = relationship("RoadProject", back_populates="road")
    complaints = relationship("Complaint", back_populates="road")
    ratings = relationship("RoadRating", back_populates="road")
    maintenance_schedules = relationship("MaintenanceSchedule", back_populates="road")

class RoadProject(Base):
    __tablename__ = "road_projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    road_id = Column(Integer, ForeignKey("roads.id", ondelete="CASCADE"), nullable=False)
    contractor_id = Column(Integer, ForeignKey("contractors.id", ondelete="SET NULL"), nullable=True)
    project_name = Column(String(255), nullable=False)
    project_type = Column(String(50), default="Maintenance")
    start_date = Column(Date)
    expected_end_date = Column(Date)
    actual_end_date = Column(Date)
    status = Column(String(20), default="Planned")
    amount_sanctioned = Column(Numeric(18, 2))
    amount_spent = Column(Numeric(18, 2), default=0)
    currency_code = Column(String(3), default="INR")
    fund_source = Column(String(200))
    tender_no = Column(String(100))
    tender_doc_url = Column(String(500))
    remarks = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    road = relationship("Road", back_populates="projects")
    contractor = relationship("Contractor", back_populates="projects")
    maintenance_schedules = relationship("MaintenanceSchedule", back_populates="project")

class MaintenanceSchedule(Base):
    __tablename__ = "maintenance_schedules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    road_id = Column(Integer, ForeignKey("roads.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("road_projects.id", ondelete="SET NULL"), nullable=True)
    scheduled_date = Column(Date, nullable=False)
    maintenance_type = Column(String(150), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="Scheduled")
    completed_date = Column(Date)
    created_at = Column(TIMESTAMP, server_default=func.now())
    road = relationship("Road", back_populates="maintenance_schedules")
    project = relationship("RoadProject", back_populates="maintenance_schedules")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(150), nullable=False)
    phone = Column(String(30), unique=True)
    email = Column(String(150), unique=True)
    password_hash = Column(String(255))
    role = Column(String(20), default="citizen")
    contractor_company = Column(String(200))
    profile_image = Column(String(500))          # NEW: profile photo path
    country_id = Column(Integer, ForeignKey("countries.id", ondelete="SET NULL"), nullable=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    country = relationship("Country", back_populates="users")
    district = relationship("District", back_populates="users")
    complaints = relationship("Complaint", back_populates="user")
    ratings = relationship("RoadRating", back_populates="user")

class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    road_id = Column(Integer, ForeignKey("roads.id", ondelete="SET NULL"), nullable=True)
    ee_id = Column(Integer, ForeignKey("executive_engineers.id", ondelete="SET NULL"), nullable=True)
    complaint_ref_no = Column(String(30), unique=True, nullable=False)
    issue_type = Column(String(50), default="Other")
    description = Column(Text, nullable=False)
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    location_text = Column(String(300))
    severity = Column(String(20), default="Medium")
    status = Column(String(20), default="Submitted")
    image_url = Column(String(500))              # NEW: complaint photo path
    yolo_detected_issues = Column(JSON)
    ai_severity_score = Column(Numeric(4, 2))
    submitted_at = Column(TIMESTAMP, server_default=func.now())
    acknowledged_at = Column(TIMESTAMP, nullable=True)
    resolved_at = Column(TIMESTAMP, nullable=True)
    resolution_notes = Column(Text)
    user = relationship("User", back_populates="complaints")
    road = relationship("Road", back_populates="complaints")
    ee = relationship("ExecutiveEngineer", back_populates="complaints")
    media = relationship("ComplaintMedia", back_populates="complaint")

class ComplaintMedia(Base):
    __tablename__ = "complaint_media"
    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(500), nullable=False)
    media_type = Column(String(10), default="image")
    yolo_result = Column(JSON)
    uploaded_at = Column(TIMESTAMP, server_default=func.now())
    complaint = relationship("Complaint", back_populates="media")

class OfflineSyncQueue(Base):
    __tablename__ = "offline_sync_queue"
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action_type = Column(String(30), nullable=False)
    payload_json = Column(Text, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(TIMESTAMP, server_default=func.now())
    synced_at = Column(TIMESTAMP, nullable=True)

class RoadRating(Base):
    __tablename__ = "road_ratings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    road_id = Column(Integer, ForeignKey("roads.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rating = Column(SmallInteger, nullable=False)
    comment = Column(Text)
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    rated_at = Column(TIMESTAMP, server_default=func.now())
    road = relationship("Road", back_populates="ratings")
    user = relationship("User", back_populates="ratings")
