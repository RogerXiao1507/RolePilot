export type Application = {
  id: number;
  selected_resume_id: number | null;
  company: string;
  role_title: string;
  status: string;
  location: string | null;
  job_url: string | null;
  job_description: string | null;
  ai_summary: string | null;
  required_skills: string[] | null;
  preferred_skills: string[] | null;
  keywords: string[] | null;
  next_steps: string[] | null;
  created_at: string;
};

export type ApplicationCreate = {
  selected_resume_id?: number | null;
  company: string;
  role_title: string;
  status?: string;
  location?: string;
  job_url?: string;
  job_description?: string;
  ai_summary?: string;
  required_skills?: string[];
  preferred_skills?: string[];
  keywords?: string[];
  next_steps?: string[];
};

export type ParsedJob = {
  company: string | null;
  role_title: string | null;
  location: string | null;
  employment_type: string | null;
  internship_season: string | null;
  required_skills: string[];
  preferred_skills: string[];
  keywords: string[];
  summary: string;
  next_steps: string[];
};

export type ResumeAnalysis = {
  summary: string
  strengths: string[]
  weaknesses: string[]
  wording_issues: string[]
  missing_metrics: string[]
  suggested_improvements: string[]
  extracted_text: string
  structured_data: ResumeStructuredData
}

export type ResumeStructuredEntry = {
  title: string
  subtitle: string | null
  location: string | null
  date_range: string | null
  bullets: string[]
}

export type ResumeStructuredData = {
  contact: {
    name: string | null
    email: string | null
    phone: string | null
    location: string | null
    links: string[]
  }
  education: ResumeStructuredEntry[]
  experience: ResumeStructuredEntry[]
  projects: ResumeStructuredEntry[]
  skills: string[]
  other: ResumeStructuredEntry[]
}

export type ResumeJobMatch = {
  overall_match_summary: string
  matched_skills: string[]
  missing_skills: string[]
  strengths_for_role: string[]
  improvement_areas: string[]
  suggested_resume_changes: string[]
}
export type SavedResume = {
  id: number
  label: string
  file_name: string
  extracted_text: string
  structured_data: ResumeStructuredData
  source_fingerprint: string
  version: number
  has_original_upload: boolean
  summary: string
  strengths: string[]
  weaknesses: string[]
  wording_issues: string[]
  missing_metrics: string[]
  suggested_improvements: string[]
  is_default: boolean
  is_archived: boolean
  created_at: string
  updated_at: string
}

export type ResumeListItem = {
  id: number
  label: string
  file_name: string
  is_default: boolean
  is_archived: boolean
  version: number
  source_fingerprint: string
  created_at: string
  updated_at: string
}

export type SavedApplicationResumeMatch = {
  id: number
  application_id: number
  resume_id: number
  resume_version: number
  is_stale: boolean
  overall_match_summary: string
  matched_skills: string[]
  missing_skills: string[]
  strengths_for_role: string[]
  improvement_areas: string[]
  suggested_resume_changes: string[]
  created_at: string
  updated_at: string
}

export type TailoredBullet = {
  section: string
  source_title: string
  original_bullet: string
  tailored_bullet: string
  evidence_used: string[]
  citations: SourceCitation[]
}

export type SourceCitation = {
  source_type: "resume_item" | "evidence"
  source_id: string
  source_version: number
}

export type TailoredResumeContent = {
  tailored_summary: string
  tailored_skills: string[]
  tailored_bullets: TailoredBullet[]
  tailoring_notes: string[]
}

export type SavedTailoredBullet = {
  section: string
  source_title: string
  original_bullet: string
  tailored_bullet: string
  evidence_used: string[]
  citations: SourceCitation[]
}

export type SavedApplicationTailoredResume = {
  id: number
  application_id: number
  resume_id: number
  resume_version: number
  is_stale: boolean
  tailored_summary: string
  tailored_skills: string[]
  tailored_bullets: SavedTailoredBullet[]
  tailoring_notes: string[]
  created_at: string
  updated_at: string
}

export type ResumeHeader = {
  name: string
  location: string | null
  phone: string | null
  email: string | null
  websites: string[]
}

export type ResumeEducationEntry = {
  school: string
  degree: string
  location: string | null
  date_range: string | null
  gpa: string | null
  coursework: string[]
}

export type ResumeBulletEntry = {
  title: string
  subtitle: string | null
  location: string | null
  date_range: string | null
  bullets: string[]
}

export type ResumeSkillsSection = {
  programming_languages: string[]
  frameworks_tools: string[]
  hardware_instrumentation: string[]
  technical_areas: string[]
  developer_tools: string[]
}

export type FullTailoredResumeDraft = {
  header: ResumeHeader
  professional_summary: string
  education: ResumeEducationEntry[]
  experience: ResumeBulletEntry[]
  projects: ResumeBulletEntry[]
  skills: ResumeSkillsSection
}

export type SavedApplicationFullResumeDraft = {
  id: number
  application_id: number
  resume_id: number
  resume_version: number
  is_stale: boolean
  draft_data: FullTailoredResumeDraft
  created_at: string
  updated_at: string
}

export type EvidenceMetric = {
  label: string
  value: string
  context: string | null
}

export type ProjectEvidence = {
  id: number
  title: string
  category: string
  description: string
  skills: string[]
  keywords: string[]
  bullet_bank: string[]
  outcome: string | null
  start_date: string | null
  end_date: string | null
  links: string[]
  verified_metrics: EvidenceMetric[]
  ai_suggested_metrics: EvidenceMetric[]
  version: number
  content_fingerprint: string
  ingestion_status: "pending" | "ready" | "failed"
  ingestion_error: string | null
  resume_source_item_id: string | null
  created_at: string
  updated_at: string
}

export type ProjectEvidenceInput = {
  title: string
  category: string
  description: string
  skills: string[]
  keywords: string[]
  bullet_bank: string[]
  outcome?: string | null
  start_date?: string | null
  end_date?: string | null
  links: string[]
  verified_metrics: EvidenceMetric[]
  resume_source_item_id?: string | null
}

export type ResumeSourceItem = {
  id: string
  resume_id: number
  source_version: number
  section: string
  item_type: string
  title: string | null
  content: string
  ordinal: number
  source_metadata: Record<string, unknown>
  is_user_verified: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export type JobRecency = "24h" | "7d" | "14d" | "30d" | "all"
export type JobSort = "recommended" | "newest" | "most_relevant"
export type DiscoveryActionState = "saved" | "dismissed" | "duplicate" | "converted"

export type JobSearchInput = {
  name: string
  resume_id: number | null
  target_titles: string[]
  adjacent_titles: string[]
  seniority_levels: string[]
  employment_types: string[]
  locations: string[]
  workplace_types: string[]
  salary_min: number | null
  salary_max: number | null
  salary_currency: string
  industries: string[]
  required_keywords: string[]
  excluded_keywords: string[]
  excluded_companies: string[]
  recency: JobRecency
  notification_frequency: "off" | "daily" | "weekly"
  is_active: boolean
}

export type JobSearch = JobSearchInput & {
  id: string
  user_id: string
  created_at: string
  updated_at: string
}

export type JobSource = {
  source_name: string
  external_job_id: string
  canonical_url: string
  source_posted_at: string | null
  source_updated_at: string | null
  last_verified_at: string
  verification_status: string
}

export type DiscoveryJob = {
  id: string
  company_name: string
  title: string
  location: string | null
  workplace_type: string | null
  employment_type: string | null
  seniority_level: string | null
  industry: string | null
  salary_min: number | null
  salary_max: number | null
  salary_currency: string | null
  description: string
  source_posted_at: string | null
  freshness_label: string
  preference_match_score: number
  resume_match_score: number | null
  recommended_score: number
  match_reasons: string[]
  action_state: DiscoveryActionState | null
  sources: JobSource[]
}

export type DiscoveryFeed = {
  search_id: string
  recency: JobRecency
  sort: JobSort
  items: DiscoveryJob[]
}

export type DiscoveryAction = {
  discovered_job_id: string
  state: DiscoveryActionState
  application_id: number | null
}

export type DiscoveryCatalogStatus = {
  configured_connector_count: number
  configured_sources: string[]
  active_job_count: number
  active_source_count: number
  last_verified_at: string | null
}
