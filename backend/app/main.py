import logging
import os
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.applications import router as applications_router
from app.api.routes.ai import router as ai_router
from app.api.routes.resume import router as resume_router
from app.api.routes.match import router as match_router
from app.api.routes.project_evidence import router as project_evidence_router
from app.api.routes.tailored_resume import router as tailored_resume_router
from app.api.routes.export import router as export_router
from app.api.routes.full_resume_draft import router as full_resume_draft_router
from app.api.routes.users import router as users_router
from app.api.routes.job_discovery import router as job_discovery_router


logger = logging.getLogger(__name__)

origins = os.getenv("ALLOWED_ORIGINS", "")
origin_list = [origin.strip() for origin in origins.split(",") if origin.strip()]

default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

allow_origins = list(dict.fromkeys(origin_list + default_origins))

app = FastAPI(title="RolePilot API")


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", uuid4().hex)
    logger.exception("Unhandled API error request_id=%s", request_id, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred.",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(applications_router)
app.include_router(ai_router)
app.include_router(resume_router)
app.include_router(match_router)
app.include_router(project_evidence_router)
app.include_router(tailored_resume_router)
app.include_router(export_router)
app.include_router(full_resume_draft_router)
app.include_router(users_router)
app.include_router(job_discovery_router)

@app.get("/")
def root():
    return {"message": "RolePilot backend is running"}

@app.get("/health")
def health():
    return {"status": "ok"}
