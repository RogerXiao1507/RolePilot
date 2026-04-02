import {
  Application,
  ApplicationCreate,
  ParsedJob,
  ResumeAnalysis,
  ResumeJobMatch,
  SavedResume,
  SavedApplicationResumeMatch,
  TailoredResumeContent,
  SavedApplicationTailoredResume,
  FullTailoredResumeDraft,
  SavedApplicationFullResumeDraft,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getApplications(): Promise<Application[]> {
  const res = await fetch(`${API_BASE}/applications`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Failed to fetch applications");
  }

  return res.json();
}

export async function createApplication(payload: ApplicationCreate): Promise<Application> {
  const res = await fetch(`${API_BASE}/applications`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Failed to create application");
  }

  return res.json();
}

export async function getApplication(id: number): Promise<Application> {
  const res = await fetch(`${API_BASE}/applications/${id}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Failed to fetch application");
  }

  return res.json();
}

export async function updateApplication(
  id: number,
  payload: Partial<ApplicationCreate>
): Promise<Application> {
  const res = await fetch(`${API_BASE}/applications/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Failed to update application");
  }

  return res.json();
}

export async function deleteApplication(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/applications/${id}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    throw new Error("Failed to delete application");
  }
}

export async function parseJobDescription(text: string): Promise<ParsedJob> {
  const res = await fetch(`${API_BASE}/ai/parse-job`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text }),
  });

  if (!res.ok) {
    throw new Error("Failed to parse job description");
  }

  return res.json();
}

export async function parseJobUrl(url: string): Promise<ParsedJob> {
  const res = await fetch(`${API_BASE}/ai/parse-job-url`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ url }),
  });

  if (!res.ok) {
    throw new Error("Failed to parse job URL");
  }

  return res.json();
}

export async function analyzeResume(file: File): Promise<ResumeAnalysis> {
  const formData = new FormData()
  formData.append("file", file)

  const res = await fetch(`${API_BASE}/resume/analyze`, {
    method: "POST",
    body: formData,
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to analyze resume")
  }

  return res.json()
}

export async function matchResumeToJob(payload: {
  resume_text: string
  role_title?: string | null
  company?: string | null
  job_summary?: string | null
  required_skills?: string[]
  preferred_skills?: string[]
  keywords?: string[]
}): Promise<ResumeJobMatch> {
  const res = await fetch(`${API_BASE}/ai/match-resume-job`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to match resume to job")
  }

  return res.json()
}

export async function saveResume(payload: {
  file_name: string
  extracted_text: string
  summary: string
  strengths: string[]
  weaknesses: string[]
  wording_issues: string[]
  missing_metrics: string[]
  suggested_improvements: string[]
}): Promise<SavedResume> {
  const res = await fetch(`${API_BASE}/resume/save`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to save resume")
  }

  return res.json()
}

export async function getLatestResume(): Promise<SavedResume> {
  const res = await fetch(`${API_BASE}/resume/latest`, {
    method: "GET",
    cache: "no-store",
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to load latest resume")
  }

  return res.json()
}

export async function saveApplicationResumeMatch(payload: {
  application_id: number
  resume_id: number
  overall_match_summary: string
  matched_skills: string[]
  missing_skills: string[]
  strengths_for_role: string[]
  improvement_areas: string[]
  suggested_resume_changes: string[]
}): Promise<SavedApplicationResumeMatch> {
  const res = await fetch(`${API_BASE}/matches`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to save application resume match")
  }

  return res.json()
}

export async function getApplicationResumeMatch(
  applicationId: number
): Promise<SavedApplicationResumeMatch> {
  const res = await fetch(`${API_BASE}/matches/application/${applicationId}`, {
    method: "GET",
    cache: "no-store",
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to load application resume match")
  }

  return res.json()
}

export async function tailorResumeForApplication(
  applicationId: number
): Promise<TailoredResumeContent> {
  const res = await fetch(`${API_BASE}/ai/tailor-resume`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ application_id: applicationId }),
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to tailor resume")
  }

  return res.json()
}

export async function saveApplicationTailoredResume(payload: {
  application_id: number
  resume_id: number
  tailored_summary: string
  tailored_skills: string[]
  tailored_bullets: {
    section: string
    source_title: string
    original_bullet: string
    tailored_bullet: string
    evidence_used: string[]
  }[]
  tailoring_notes: string[]
}): Promise<SavedApplicationTailoredResume> {
  const res = await fetch(`${API_BASE}/tailored-resumes`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to save tailored resume")
  }

  return res.json()
}

export async function getApplicationTailoredResume(
  applicationId: number
): Promise<SavedApplicationTailoredResume> {
  const res = await fetch(`${API_BASE}/tailored-resumes/application/${applicationId}`, {
    method: "GET",
    cache: "no-store",
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to load tailored resume")
  }

  return res.json()
}

export async function getFullTailoredResumeDraft(
  applicationId: number
): Promise<FullTailoredResumeDraft> {
  const res = await fetch(`${API_BASE}/ai/full-tailored-resume`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ application_id: applicationId }),
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to generate full tailored resume draft")
  }

  return res.json()
}

export async function downloadTailoredResumeDocx(applicationId: number): Promise<Blob> {
  const res = await fetch(`${API_BASE}/export/tailored-resume-docx`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ application_id: applicationId }),
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to export DOCX")
  }

  return res.blob()
}

export async function downloadTailoredResumePdf(applicationId: number): Promise<Blob> {
  const res = await fetch(`${API_BASE}/export/tailored-resume-pdf`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ application_id: applicationId }),
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to export PDF")
  }

  return res.blob()
}
export async function saveFullResumeDraft(payload: {
  application_id: number
  resume_id: number
  draft_data: FullTailoredResumeDraft
}): Promise<SavedApplicationFullResumeDraft> {
  const res = await fetch(`${API_BASE}/full-resume-drafts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to save full resume draft")
  }

  return res.json()
}

export async function getSavedFullResumeDraft(
  applicationId: number
): Promise<SavedApplicationFullResumeDraft> {
  const res = await fetch(`${API_BASE}/full-resume-drafts/application/${applicationId}`, {
    method: "GET",
    cache: "no-store",
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to load saved full resume draft")
  }

  return res.json()
}