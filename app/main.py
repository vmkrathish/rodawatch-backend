# RoadWatch – developed by M K Rathish and team
# IIT Madras CoERS Road Safety Hackathon 2026
# All rights reserved.

import os, sqlite3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.database import engine, Base
from app.core.config import settings
from app.routers import auth, roads, complaints, ratings, sync, dashboard, engineers
from app.routers import admin, contractor, location, profile

def _run_migrations():
    if not settings.DATABASE_URL.startswith("sqlite"): return
    db_path = settings.DATABASE_URL.replace("sqlite:///./", "").replace("sqlite:///", "")
    if not os.path.exists(db_path): return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    migrations = [
        ("users",      "contractor_company", "VARCHAR(200)"),
        ("users",      "profile_image",      "VARCHAR(500)"),   # NEW
        ("complaints", "image_url",          "VARCHAR(500)"),   # NEW
    ]
    for table, col, col_def in migrations:
        try:
            cur.execute(f"PRAGMA table_info({table})")
            if col not in [r[1] for r in cur.fetchall()]:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
                print(f"[Migration] Added {table}.{col}")
        except Exception as e:
            print(f"[Migration] Skipped {table}.{col}: {e}")
    conn.commit(); conn.close()

_run_migrations()
Base.metadata.create_all(bind=engine)
for d in ["./uploads/complaints", "./uploads/media", "./uploads/profiles"]:
    os.makedirs(d, exist_ok=True)

app = FastAPI(title="RoadWatch API", version="2.2.0", docs_url="/docs", redoc_url="/redoc")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/uploads", StaticFiles(directory="./uploads"), name="uploads")

for r in [auth, roads, complaints, ratings, sync, dashboard, engineers, admin, contractor, location, profile]:
    app.include_router(r.router, prefix="/api/v1")

@app.get("/", tags=["Health"])
def root(): return {"app": "RoadWatch API", "version": "2.2.0", "status": "running"}

@app.get("/health", tags=["Health"])
def health(): return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
