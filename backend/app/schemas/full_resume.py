from pydantic import BaseModel


class ResumeHeader(BaseModel):
    name: str
    location: str | None = None
    phone: str | None = None
    email: str | None = None
    websites: list[str] = []


class ResumeEducationEntry(BaseModel):
    school: str
    degree: str
    location: str | None = None
    date_range: str | None = None
    gpa: str | None = None
    coursework: list[str] = []


class ResumeBulletEntry(BaseModel):
    title: str
    subtitle: str | None = None
    location: str | None = None
    date_range: str | None = None
    bullets: list[str]


class ResumeSkillsSection(BaseModel):
    programming_languages: list[str] = []
    frameworks_tools: list[str] = []
    hardware_instrumentation: list[str] = []
    technical_areas: list[str] = []
    developer_tools: list[str] = []


class FullTailoredResumeDraftResponse(BaseModel):
    header: ResumeHeader
    professional_summary: str
    education: list[ResumeEducationEntry]
    experience: list[ResumeBulletEntry]
    projects: list[ResumeBulletEntry]
    skills: ResumeSkillsSection