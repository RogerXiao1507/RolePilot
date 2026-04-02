from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
from app.models.application import Application
from app.models.resume import Resume
from app.models.application_resume_match import ApplicationResumeMatch
from app.api.routes.applications import router as applications_router
from app.api.routes.ai import router as ai_router
from app.api.routes.resume import router as resume_router
from app.api.routes.match import router as match_router
from app.models.project_evidence import ProjectEvidence
from app.api.routes.project_evidence import router as project_evidence_router
from app.models.project_evidence_chunk import ProjectEvidenceChunk
from app.models.application_tailored_resume import ApplicationTailoredResume
from app.api.routes.tailored_resume import router as tailored_resume_router
from app.api.routes.export import router as export_router
from app.models.application_full_resume_draft import ApplicationFullResumeDraft
from app.api.routes.full_resume_draft import router as full_resume_draft_router

import os

origins = os.getenv("ALLOWED_ORIGINS", "")
origin_list = [origin.strip() for origin in origins.split(",") if origin.strip()]

app = FastAPI(title="RolePilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://10.192.100.197:3000",
        "https://rolepilot-nu.vercel.app/",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(applications_router)
app.include_router(ai_router)
app.include_router(resume_router)
app.include_router(match_router)
app.include_router(project_evidence_router)
app.include_router(tailored_resume_router)
app.include_router(export_router)
app.include_router(full_resume_draft_router)

@app.get("/")
def root():
    return {"message": "RolePilot backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}