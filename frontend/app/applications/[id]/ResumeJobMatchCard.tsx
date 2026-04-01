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
      setError("No saved resume found. Please upload and analyze a resume first.")
      return
    }

    if (!savedResume.extracted_text?.trim()) {
      setError("Saved resume text is missing. Please re-upload your resume.")
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
      setError("Failed to match resume to job.")
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
      return { label: "Strong Fit", classes: "border-emerald-800 bg-emerald-950/60 text-emerald-300" }
    }

    if (
      summary.includes("moderate") ||
      summary.includes("some gaps") ||
      summary.includes("mixed fit")
    ) {
      return { label: "Moderate Fit", classes: "border-amber-800 bg-amber-950/60 text-amber-300" }
    }

    return { label: "Needs Work", classes: "border-red-800 bg-red-950/60 text-red-300" }
  }, [result])

  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-white">Resume Match</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-400">
            Compare your latest saved resume against this job.
          </p>
        </div>

        {fitLabel && (
          <span
            className={`rounded-full border px-3 py-1 text-xs font-medium ${fitLabel.classes}`}
          >
            {fitLabel.label}
          </span>
        )}
      </div>

      <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-900/60 p-4">
        <p className="text-xs uppercase tracking-wide text-zinc-500">
          Current Saved Resume
        </p>
        <p className="mt-2 text-sm text-zinc-200">
          {savedResume ? savedResume.file_name : "No saved resume found"}
        </p>

        {savedMatchMeta && (
          <p className="mt-2 text-xs text-zinc-500">
            Last matched: {new Date(savedMatchMeta.updated_at).toLocaleString()}
          </p>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-red-800 bg-red-950/50 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="mt-4">
        <button
          onClick={handleMatchResume}
          disabled={loading || !savedResume}
          className="w-full rounded-xl border border-emerald-700 bg-emerald-600 px-4 py-3 text-sm font-medium text-white transition hover:border-emerald-600 hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Matching..." : result ? "Refresh Match" : "Match Resume to Job"}
        </button>
      </div>

      {loadingSavedMatch && !result && (
        <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
          <p className="text-sm text-zinc-400">Loading saved match...</p>
        </div>
      )}

      {!loadingSavedMatch && !result && !loading && !error && (
        <div className="mt-4 rounded-xl border border-dashed border-zinc-800 bg-zinc-900/40 p-4">
          <p className="text-sm text-zinc-400">
            No saved match yet for this application.
          </p>
        </div>
      )}

      {result && !loading && (
        <div className="mt-5 space-y-4">
          <SectionCard title="Overall Match Summary">
            <p className="text-sm leading-7 text-zinc-200">
              {result.overall_match_summary}
            </p>
          </SectionCard>

          <AnalysisCard title="Matched Skills" items={result.matched_skills} />
          <AnalysisCard title="Missing Skills" items={result.missing_skills} />
          <AnalysisCard title="Strengths for Role" items={result.strengths_for_role} />
          <AnalysisCard title="Improvement Areas" items={result.improvement_areas} />
          <AnalysisCard
            title="Suggested Resume Changes"
            items={result.suggested_resume_changes}
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
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 shadow-sm">
      <h3 className="mb-3 text-lg font-semibold text-white">{title}</h3>
      {children}
    </section>
  )
}

function AnalysisCard({
  title,
  items,
}: {
  title: string
  items: string[]
}) {
  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 shadow-sm">
      <h3 className="mb-3 text-lg font-semibold text-white">{title}</h3>

      {items.length === 0 ? (
        <p className="text-sm text-zinc-500">No items found.</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item, index) => (
            <li
              key={index}
              className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-3 text-sm leading-6 text-zinc-200"
            >
              {item}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}