"use client"

import { useEffect, useState } from "react"
import {
  getApplicationTailoredResume,
  getLatestResume,
  saveApplicationTailoredResume,
  tailorResumeForApplication,
} from "@/lib/api"
import type {
  SavedApplicationTailoredResume,
  SavedResume,
  TailoredResumeContent,
} from "@/lib/types"

type TailoredResumeCardProps = {
  applicationId: number
}

export default function TailoredResumeCard({
  applicationId,
}: TailoredResumeCardProps) {
  const [loading, setLoading] = useState(false)
  const [loadingSavedTailoredResume, setLoadingSavedTailoredResume] = useState(true)
  const [error, setError] = useState("")
  const [savedResume, setSavedResume] = useState<SavedResume | null>(null)
  const [savedTailoredMeta, setSavedTailoredMeta] =
    useState<SavedApplicationTailoredResume | null>(null)
  const [result, setResult] = useState<TailoredResumeContent | null>(null)

  useEffect(() => {
    async function loadData() {
      try {
        const resume = await getLatestResume()
        setSavedResume(resume)
      } catch (err) {
        console.error(err)
      }

      try {
        const savedTailored = await getApplicationTailoredResume(applicationId)

        setSavedTailoredMeta(savedTailored)
        setResult({
          tailored_summary: savedTailored.tailored_summary,
          tailored_skills: savedTailored.tailored_skills,
          tailored_bullets: savedTailored.tailored_bullets,
          tailoring_notes: savedTailored.tailoring_notes,
        })
      } catch (err) {
        console.error(err)
      } finally {
        setLoadingSavedTailoredResume(false)
      }
    }

    loadData()
  }, [applicationId])

  async function handleTailorResume() {
    setLoading(true)
    setError("")

    try {
      if (!savedResume) {
        throw new Error("No saved resume found")
      }

      const data = await tailorResumeForApplication(applicationId)

      const saved = await saveApplicationTailoredResume({
        application_id: applicationId,
        resume_id: savedResume.id,
        tailored_summary: data.tailored_summary,
        tailored_skills: data.tailored_skills,
        tailored_bullets: data.tailored_bullets,
        tailoring_notes: data.tailoring_notes,
      })

      setSavedTailoredMeta(saved)
      setResult(data)
    } catch (err) {
      console.error(err)
      setError("Failed to tailor resume for this application.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-6 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white">Tailored Resume Draft</h2>
          <p className="mt-2 text-sm text-zinc-400">
            Generate tailored sections and bullets for this job using your saved resume and retrieved project evidence.
          </p>
        </div>

        <button
          onClick={handleTailorResume}
          disabled={loading || !savedResume}
          className="rounded-xl border border-emerald-700 bg-emerald-600 px-5 py-3 text-sm font-medium text-white transition hover:border-emerald-600 hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Tailoring..." : result ? "Refresh Tailored Resume" : "Tailor Resume for This Job"}
        </button>
      </div>

      <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-900/60 p-4">
        <p className="text-xs uppercase tracking-wide text-zinc-500">
          Current Saved Resume
        </p>
        <p className="mt-2 text-sm text-zinc-200">
          {savedResume ? savedResume.file_name : "No saved resume found"}
        </p>

        {savedTailoredMeta && (
          <p className="mt-2 text-xs text-zinc-500">
            Last tailored: {new Date(savedTailoredMeta.updated_at).toLocaleString()}
          </p>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-red-800 bg-red-950/50 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {loadingSavedTailoredResume && !result && (
        <div className="mt-6 rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
          <p className="text-sm text-zinc-400">Loading saved tailored resume...</p>
        </div>
      )}

      {!result && !loading && !loadingSavedTailoredResume && !error && (
        <div className="mt-6 rounded-xl border border-dashed border-zinc-800 bg-zinc-900/40 p-5">
          <p className="text-sm text-zinc-400">
            Click the button above to generate tailored bullets and sections for this application.
          </p>
        </div>
      )}

      {result && !loading && (
        <div className="mt-6 space-y-6">
          <SectionCard title="Tailored Summary">
            <p className="text-base leading-8 text-zinc-200">
              {result.tailored_summary}
            </p>
          </SectionCard>

          <SectionCard title="Tailored Skills">
            {result.tailored_skills.length === 0 ? (
              <p className="text-zinc-500">No tailored skills returned.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {result.tailored_skills.map((skill, index) => (
                  <span
                    key={`${skill}-${index}`}
                    className="rounded-full border border-emerald-800 bg-emerald-950/60 px-3 py-1 text-sm text-emerald-300"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard title="Tailored Bullets">
            {result.tailored_bullets.length === 0 ? (
              <p className="text-zinc-500">No tailored bullets returned.</p>
            ) : (
              <div className="space-y-4">
                {result.tailored_bullets.map((bullet, index) => (
                  <div
                    key={index}
                    className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full border border-zinc-700 bg-zinc-950 px-3 py-1 text-xs text-zinc-300">
                        {bullet.section}
                      </span>
                      <span className="rounded-full border border-blue-800 bg-blue-950/60 px-3 py-1 text-xs text-blue-300">
                        {bullet.source_title}
                      </span>
                    </div>

                    <div className="mt-4">
                      <p className="text-xs uppercase tracking-wide text-zinc-500">
                        Replace this bullet
                      </p>
                      <p className="mt-2 rounded-lg border border-zinc-800 bg-zinc-950/80 p-3 text-sm leading-6 text-zinc-300">
                        {bullet.original_bullet || "No original bullet identified."}
                      </p>
                    </div>

                    <div className="mt-4">
                      <p className="text-xs uppercase tracking-wide text-zinc-500">
                        Use this tailored bullet
                      </p>
                      <p className="mt-2 rounded-lg border border-emerald-800 bg-emerald-950/20 p-3 text-sm leading-6 text-zinc-100">
                        {bullet.tailored_bullet}
                      </p>
                    </div>

                    {bullet.evidence_used.length > 0 && (
                      <div className="mt-4">
                        <p className="text-xs uppercase tracking-wide text-zinc-500">
                          Evidence Used
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {bullet.evidence_used.map((item, evidenceIndex) => (
                            <span
                              key={`${item}-${evidenceIndex}`}
                              className="rounded-full border border-purple-800 bg-purple-950/40 px-3 py-1 text-xs text-purple-300"
                            >
                              {item}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard title="Tailoring Notes">
            {result.tailoring_notes.length === 0 ? (
              <p className="text-zinc-500">No tailoring notes returned.</p>
            ) : (
              <ul className="list-disc space-y-2 pl-5 text-zinc-200">
                {result.tailoring_notes.map((note, index) => (
                  <li key={index}>{note}</li>
                ))}
              </ul>
            )}
          </SectionCard>
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
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 shadow-sm">
      <h3 className="mb-4 text-xl font-semibold text-white">{title}</h3>
      {children}
    </section>
  )
}