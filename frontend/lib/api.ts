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
  ResumeListItem,
  ResumeStructuredData,
  ProjectEvidence,
  ProjectEvidenceInput,
  ResumeSourceItem,
  DiscoveryAction,
  DiscoveryCatalogStatus,
  DiscoveryActionState,
  DiscoveryFeed,
  JobRecency,
  JobSearch,
  JobSearchInput,
  JobSort,
} from "@/lib/types";

const API_BASE = "/api/backend";

async function apiError(res: Response, fallback: string): Promise<Error> {
  try {
    const body = await res.json() as { detail?: string | Array<{ msg?: string }> }
    if (typeof body.detail === "string") return new Error(body.detail)
    if (Array.isArray(body.detail)) {
      return new Error(body.detail.map((item) => item.msg).filter(Boolean).join(" ") || fallback)
    }
  } catch {
    // Fall through to the user-safe message.
  }
  return new Error(fallback)
}

async function responseJson<T>(res: Response, fallback: string): Promise<T> {
  try {
    return await res.json() as T
  } catch {
    throw new Error(`${fallback} The server returned an incomplete response; please retry.`)
  }
}

export async function getJobSearches(): Promise<JobSearch[]> {
  const res = await fetch(`${API_BASE}/job-discovery/searches`, { cache: "no-store" })
  if (!res.ok) throw await apiError(res, "Could not load saved searches.")
  return responseJson<JobSearch[]>(res, "Could not load saved searches.")
}

export async function getDiscoveryCatalogStatus(): Promise<DiscoveryCatalogStatus> {
  const res = await fetch(`${API_BASE}/job-discovery/status`, { cache: "no-store" })
  if (!res.ok) throw await apiError(res, "Could not load discovery catalog status.")
  return responseJson<DiscoveryCatalogStatus>(res, "Could not load discovery catalog status.")
}

export async function createJobSearch(payload: JobSearchInput): Promise<JobSearch> {
  const res = await fetch(`${API_BASE}/job-discovery/searches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw await apiError(res, "Could not create the saved search.")
  return responseJson<JobSearch>(res, "Could not create the saved search.")
}

export async function updateJobSearch(
  id: string,
  payload: Partial<JobSearchInput>
): Promise<JobSearch> {
  const res = await fetch(`${API_BASE}/job-discovery/searches/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw await apiError(res, "Could not update the saved search.")
  return responseJson<JobSearch>(res, "Could not update the saved search.")
}

export async function deleteJobSearch(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/job-discovery/searches/${id}`, { method: "DELETE" })
  if (!res.ok) throw await apiError(res, "Could not delete the saved search.")
}

export async function getDiscoveryFeed(params: {
  searchId: string
  recency: JobRecency
  sort: JobSort
}): Promise<DiscoveryFeed> {
  const query = new URLSearchParams({
    search_id: params.searchId,
    recency: params.recency,
    sort: params.sort,
  })
  const res = await fetch(`${API_BASE}/job-discovery/feed?${query}`, { cache: "no-store" })
  if (!res.ok) throw await apiError(res, "Could not load discovered jobs.")
  return responseJson<DiscoveryFeed>(res, "Could not load discovered jobs.")
}

export async function setDiscoveryAction(
  jobId: string,
  state: Exclude<DiscoveryActionState, "converted">
): Promise<DiscoveryAction> {
  const res = await fetch(`${API_BASE}/job-discovery/jobs/${jobId}/action`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state }),
  })
  if (!res.ok) throw await apiError(res, "Could not update that job.")
  return responseJson<DiscoveryAction>(res, "Could not update that job.")
}

export async function clearDiscoveryAction(jobId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/job-discovery/jobs/${jobId}/action`, {
    method: "DELETE",
  })
  if (!res.ok) throw await apiError(res, "Could not clear that job action.")
}

export async function convertDiscoveryJob(
  jobId: string,
  searchId: string
): Promise<DiscoveryAction & { application_id: number }> {
  const res = await fetch(`${API_BASE}/job-discovery/jobs/${jobId}/convert`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ search_id: searchId }),
  })
  if (!res.ok) throw await apiError(res, "Could not convert this job to an application.")
  return responseJson<DiscoveryAction & { application_id: number }>(
    res,
    "Could not convert this job to an application."
  )
}

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

export async function uploadResume(
  file: File,
  label: string,
  makeDefault: boolean
): Promise<SavedResume> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("label", label)
  formData.append("make_default", String(makeDefault))
  const res = await fetch(`${API_BASE}/resume/upload`, {
    method: "POST",
    body: formData,
  })
  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to upload and analyze resume")
  }
  return res.json()
}

export async function matchResumeToJob(payload: {
  application_id: number
  resume_id: number
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
  label?: string
  make_default?: boolean
  file_name: string
  extracted_text: string
  structured_data: ResumeStructuredData
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

export async function getResumes(includeArchived = false): Promise<ResumeListItem[]> {
  const query = includeArchived ? "?include_archived=true" : ""
  const res = await fetch(`${API_BASE}/resume${query}`, {
    method: "GET",
    cache: "no-store",
  })

  if (!res.ok) {
    throw new Error("Failed to load resumes")
  }
  return res.json()
}

export async function getResume(id: number): Promise<SavedResume> {
  const res = await fetch(`${API_BASE}/resume/${id}`, {
    method: "GET",
    cache: "no-store",
  })

  if (!res.ok) {
    throw new Error("Failed to load resume")
  }
  return res.json()
}

export async function updateResume(
  id: number,
  payload: { label?: string; is_default?: true; is_archived?: boolean }
): Promise<SavedResume> {
  const res = await fetch(`${API_BASE}/resume/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to update resume")
  }
  return res.json()
}

export async function updateResumeStructuredData(
  id: number,
  structuredData: ResumeStructuredData
): Promise<SavedResume> {
  const res = await fetch(`${API_BASE}/resume/${id}/structured-data`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ structured_data: structuredData }),
  })
  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to update parsed resume")
  }
  return res.json()
}

export async function getResumeSourceItems(id: number): Promise<ResumeSourceItem[]> {
  const res = await fetch(`${API_BASE}/resume/${id}/source-items`, {
    cache: "no-store",
  })
  if (!res.ok) throw new Error("Failed to load resume source items")
  return res.json()
}

export async function getResumeSourceUrl(id: number): Promise<{ url: string; expires_in_seconds: number }> {
  const res = await fetch(`${API_BASE}/resume/${id}/source-url`, { cache: "no-store" })
  if (!res.ok) throw new Error("Failed to create a private resume link")
  return res.json()
}

export async function convertResumeSourceToEvidence(
  sourceItemId: string,
  payload: { title?: string; category?: string; outcome?: string; skills?: string[] }
): Promise<ProjectEvidence> {
  const res = await fetch(`${API_BASE}/project-evidence/from-resume-source/${sourceItemId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to convert resume source")
  }
  return res.json()
}

export async function deleteResume(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/resume/${id}`, { method: "DELETE" })
  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to delete resume")
  }
}

export async function getProjectEvidence(): Promise<ProjectEvidence[]> {
  const res = await fetch(`${API_BASE}/project-evidence`, { cache: "no-store" })
  if (!res.ok) throw new Error("Failed to load evidence")
  return res.json()
}

export async function createProjectEvidence(
  payload: ProjectEvidenceInput
): Promise<ProjectEvidence> {
  const res = await fetch(`${API_BASE}/project-evidence`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to create evidence")
  }
  return res.json()
}

export async function updateProjectEvidence(
  id: number,
  payload: Partial<ProjectEvidenceInput>
): Promise<ProjectEvidence> {
  const res = await fetch(`${API_BASE}/project-evidence/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || "Failed to update evidence")
  }
  return res.json()
}

export async function deleteProjectEvidence(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/project-evidence/${id}`, { method: "DELETE" })
  if (!res.ok) throw new Error("Failed to delete evidence")
}

export async function retryProjectEvidence(id: number): Promise<ProjectEvidence> {
  const res = await fetch(`${API_BASE}/project-evidence/${id}/retry`, {
    method: "POST",
  })
  if (!res.ok) throw new Error("Failed to retry evidence ingestion")
  return res.json()
}

export async function confirmProjectEvidenceMetric(
  id: number,
  suggestionIndex: number
): Promise<ProjectEvidence> {
  const res = await fetch(`${API_BASE}/project-evidence/${id}/confirm-metric`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ suggestion_index: suggestionIndex }),
  })
  if (!res.ok) throw new Error("Failed to confirm suggested metric")
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
  applicationId: number,
  resumeId: number
): Promise<TailoredResumeContent> {
  const res = await fetch(`${API_BASE}/ai/tailor-resume`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ application_id: applicationId, resume_id: resumeId }),
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
    citations: { source_type: "resume_item" | "evidence"; source_id: string; source_version: number }[]
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
  applicationId: number,
  resumeId: number
): Promise<FullTailoredResumeDraft> {
  const res = await fetch(`${API_BASE}/ai/full-tailored-resume`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ application_id: applicationId, resume_id: resumeId }),
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
