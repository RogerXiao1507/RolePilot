"use client"

import { useEffect, useMemo, useState } from "react"
import {
  getApplicationResumeMatch,
  getLatestResume,
  matchResumeToJob,
  saveApplicationResumeMatch,
} from "@/lib/api"
import type {
  ResumeJobMatch,
  SavedApplicationResumeMatch,
  SavedResume,
} from "@/lib/types"

type ResumeJobMatchCardProps = {
  applicationId: number
  company: string
  roleTitle: string
  jobSummary?: string | null
  requiredSkills?: string[]
  preferredSkills?: string[]
  keywords?: string[]
}

export default function ResumeJobMatchCard({
  applicationId,
  company,
  roleTitle,
  jobSummary,
  requiredSkills = [],
  preferredSkills = [],
  keywords = [],
}: ResumeJobMatchCardProps) {
  const [loading, setLoading] = useState(false)
  const [loadingSavedMatch, setLoadingSavedMatch] = useState(true)
  const [error, setError] = useState("")
  const [savedResume, setSavedResume] = useState<SavedResume | null>(null)
  const [savedMatchMeta, setSavedMatchMeta] =
    useState<SavedApplicationResumeMatch | null>(null)
  const [result, setResult] = useState<ResumeJobMatch | null>(null)

  useEffect(() => {
    async function loadData() {
      try {
        const resume = await getLatestResume()
        setSavedResume(resume)
      } catch (err) {
        console.error(err)
      }

      try {
        const savedMatch = await getApplicationResumeMatch(applicationId)
        setSavedMatchMeta(savedMatch)
        setResult({
          overall_match_summary: savedMatch.overall_match_summary,
          matched_skills: savedMatch.matched_skills,
          missing_skills: savedMatch.missing_skills,
          strengths_for_role: savedMatch.strengths_for_role,
          improvement_areas: savedMatch.improvement_areas,
          suggested_resume_changes: savedMatch.suggested_resume_changes,
        })
      } catch (err) {
        console.error(err)
      } finally {
        setLoadingSavedMatch(false)
      }
    }

    loadData()
  }, [applicationId])

  async function handleMatchResume() {
    setError("")

    if (!savedResume) {
      setError("No saved resume found. Upload and analyze a resume before matching.")
      return
    }

    if (!savedResume.extracted_text?.trim()) {
      setError("Saved resume text is missing. Re-upload your resume to rebuild the match input.")
      return
    }

    setLoading(true)

    try {
      const data = await matchResumeToJob({
        resume_text: savedResume.extracted_text,
        role_title: roleTitle,
        company,
        job_summary: jobSummary || "",
        required_skills: requiredSkills,
        preferred_skills: preferredSkills,
        keywords,
      })

      const saved = await saveApplicationResumeMatch({
        application_id: applicationId,
        resume_id: savedResume.id,
        overall_match_summary: data.overall_match_summary,
        matched_skills: data.matched_skills,
        missing_skills: data.missing_skills,
        strengths_for_role: data.strengths_for_role,
        improvement_areas: data.improvement_areas,
        suggested_resume_changes: data.suggested_resume_changes,
      })

      setSavedMatchMeta(saved)
      setResult(data)
    } catch (err) {
      console.error(err)
      setError("Resume matching failed. Check that the backend and saved resume are available.")
    } finally {
      setLoading(false)
    }
  }

  const fitLabel = useMemo(() => {
    if (!result) return null

    const summary = result.overall_match_summary.toLowerCase()

    if (
      summary.includes("strong fit") ||
      summary.includes("excellent fit") ||
      summary.includes("good fit")
    ) {
      return {
        label: "Strong Fit",
        classes: "border-emerald-200 bg-emerald-50 text-emerald-800",
      }
    }

    if (
      summary.includes("moderate") ||
      summary.includes("some gaps") ||
      summary.includes("mixed fit")
    ) {
      return {
        label: "Moderate Fit",
        classes: "border-amber-200 bg-amber-50 text-amber-800",
      }
    }

    return { label: "Needs Work", classes: "border-red-200 bg-red-50 text-red-700" }
  }, [result])

  return (
    <section className="rp-panel rp-section">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="rp-eyebrow">Resume fit</p>
          <h2 className="rp-section-title mt-2">Match scorecard</h2>
          <p className="rp-section-copy">
            Compare your latest saved resume against this role.
          </p>
        </div>

        {fitLabel && <span className={`rp-badge ${fitLabel.classes}`}>{fitLabel.label}</span>}
      </div>

      <div className="mt-5 rounded-lg border border-[var(--border)] bg-white p-4">
        <p className="rp-eyebrow">Current resume</p>
        <p className="mt-2 text-sm font-semibold">
          {savedResume ? savedResume.file_name : "No saved resume found"}
        </p>

        {savedMatchMeta && (
          <p className="mt-2 text-xs text-[var(--muted)]">
            Last matched: {new Date(savedMatchMeta.updated_at).toLocaleString()}
          </p>
        )}
      </div>

      {error && <div className="rp-error mt-4">{error}</div>}

      <button
        onClick={handleMatchResume}
        disabled={loading || !savedResume}
        className="rp-button-primary mt-4 w-full"
      >
        {loading ? "Matching Resume..." : result ? "Refresh Match" : "Match Resume to Job"}
      </button>

      {loadingSavedMatch && !result && (
        <div className="mt-4 space-y-3">
          <div className="rp-skeleton h-5 w-3/4" />
          <div className="rp-skeleton h-16 w-full" />
        </div>
      )}

      {!loadingSavedMatch && !result && !loading && !error && (
        <div className="rp-empty mt-4">
          <p className="text-sm font-bold">No match yet</p>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
            Run a match to see strengths, gaps, and suggested resume edits.
          </p>
        </div>
      )}

      {result && !loading && (
        <div className="mt-5 space-y-4">
          <SectionCard title="Overall Summary">
            <p className="text-sm leading-7 text-[var(--foreground)]">
              {result.overall_match_summary}
            </p>
          </SectionCard>

          <AnalysisCard title="Matched Skills" items={result.matched_skills} tone="accent" />
          <AnalysisCard title="Missing Skills" items={result.missing_skills} tone="danger" />
          <AnalysisCard title="Strengths for Role" items={result.strengths_for_role} tone="info" />
          <AnalysisCard title="Improvement Areas" items={result.improvement_areas} tone="warning" />
          <AnalysisCard
            title="Suggested Resume Changes"
            items={result.suggested_resume_changes}
            tone="neutral"
          />
        </div>
      )}
    </section>
  )
}

function SectionCard({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <section className="rounded-lg border border-[var(--border)] bg-white p-4">
      <h3 className="mb-3 text-sm font-bold">{title}</h3>
      {children}
    </section>
  )
}

function AnalysisCard({
  title,
  items,
  tone,
}: {
  title: string
  items: string[]
  tone: "accent" | "danger" | "info" | "neutral" | "warning"
}) {
  const toneClasses = {
    accent: "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]",
    danger: "border-red-200 bg-red-50 text-red-700",
    info: "border-blue-200 bg-blue-50 text-blue-700",
    neutral: "border-zinc-300 bg-zinc-100 text-zinc-700",
    warning: "border-amber-200 bg-amber-50 text-amber-800",
  }

  return (
    <section className="rounded-lg border border-[var(--border)] bg-white p-4">
      <h3 className="mb-3 text-sm font-bold">{title}</h3>

      {items.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">No items found.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item, index) => (
            <li key={`${item}-${index}`} className={`rp-badge block rounded-lg ${toneClasses[tone]}`}>
              {item}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
