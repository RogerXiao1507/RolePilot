export type Application = {
  id: number;
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
  file_name: string
  extracted_text: string
  summary: string
  strengths: string[]
  weaknesses: string[]
  wording_issues: string[]
  missing_metrics: string[]
  suggested_improvements: string[]
  created_at: string
}

export type SavedApplicationResumeMatch = {
  id: number
  application_id: number
  resume_id: number
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
}

export type SavedApplicationTailoredResume = {
  id: number
  application_id: number
  resume_id: number
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
  draft_data: FullTailoredResumeDraft
  created_at: string
  updated_at: string
}