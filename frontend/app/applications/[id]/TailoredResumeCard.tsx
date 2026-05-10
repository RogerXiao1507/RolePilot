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
      setError("Tailored resume generation failed. Confirm a resume is saved and try again.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="rp-panel rp-section">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="rp-eyebrow">Tailoring flow</p>
          <h2 className="rp-section-title mt-2">Targeted resume content</h2>
          <p className="rp-section-copy">
            Generate tailored sections and bullets for this role using the saved resume
            and retrieved project evidence.
          </p>
        </div>

        <button
          onClick={handleTailorResume}
          disabled={loading || !savedResume}
          className="rp-button-primary"
        >
          {loading ? "Tailoring Resume..." : result ? "Refresh Tailored Resume" : "Tailor Resume"}
        </button>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-[var(--border)] bg-white p-4">
          <p className="rp-eyebrow">Saved resume</p>
          <p className="mt-2 text-sm font-semibold">
            {savedResume ? savedResume.file_name : "No saved resume found"}
          </p>
        </div>

        <div className="rounded-lg border border-[var(--border)] bg-white p-4">
          <p className="rp-eyebrow">Tailored state</p>
          <p className="mt-2 text-sm font-semibold">
            {savedTailoredMeta
              ? `Last tailored ${new Date(savedTailoredMeta.updated_at).toLocaleString()}`
              : "No saved tailored draft"}
          </p>
        </div>
      </div>

      {error && <div className="rp-error mt-4">{error}</div>}

      {loadingSavedTailoredResume && !result && (
        <div className="mt-6 space-y-3">
          <div className="rp-skeleton h-5 w-1/3" />
          <div className="rp-skeleton h-20 w-full" />
          <div className="rp-skeleton h-20 w-full" />
        </div>
      )}

      {!result && !loading && !loadingSavedTailoredResume && !error && (
        <div className="rp-empty mt-6">
          <p className="text-sm font-bold">No tailored resume yet</p>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
            Generate tailored content after a resume has been saved. The output appears
            here and can feed the full resume draft.
          </p>
        </div>
      )}

      {result && !loading && (
        <div className="mt-6 space-y-5">
          <SectionCard title="Tailored Summary">
            <p className="text-sm leading-7 text-[var(--foreground)]">
              {result.tailored_summary}
            </p>
          </SectionCard>

          <SectionCard title="Tailored Skills">
            {result.tailored_skills.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">No tailored skills returned.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {result.tailored_skills.map((skill, index) => (
                  <span
                    key={`${skill}-${index}`}
                    className="rp-badge border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard title="Tailored Bullets">
            {result.tailored_bullets.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">No tailored bullets returned.</p>
            ) : (
              <div className="space-y-4">
                {result.tailored_bullets.map((bullet, index) => (
                  <article
                    key={`${bullet.tailored_bullet}-${index}`}
                    className="rounded-lg border border-[var(--border)] bg-white p-4"
                  >
                    <div className="flex flex-wrap gap-2">
                      <span className="rp-badge">{bullet.section}</span>
                      <span className="rp-badge border-blue-200 bg-blue-50 text-blue-700">
                        {bullet.source_title}
                      </span>
                    </div>

                    <div className="mt-4 grid gap-4 lg:grid-cols-2">
                      <BulletBlock
                        label="Replace this bullet"
                        text={bullet.original_bullet || "No original bullet identified."}
                      />
                      <BulletBlock label="Use this tailored bullet" text={bullet.tailored_bullet} />
                    </div>

                    {bullet.evidence_used.length > 0 && (
                      <div className="mt-4">
                        <p className="rp-eyebrow">Evidence used</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {bullet.evidence_used.map((item, evidenceIndex) => (
                            <span
                              key={`${item}-${evidenceIndex}`}
                              className="rp-badge border-amber-200 bg-amber-50 text-amber-800"
                            >
                              {item}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard title="Tailoring Notes">
            {result.tailoring_notes.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">No tailoring notes returned.</p>
            ) : (
              <ul className="space-y-2">
                {result.tailoring_notes.map((note, index) => (
                  <li
                    key={`${note}-${index}`}
                    className="rounded-lg border border-[var(--border)] bg-white p-3 text-sm leading-6"
                  >
                    {note}
                  </li>
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
    <section className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] p-5">
      <h3 className="mb-4 text-sm font-bold">{title}</h3>
      {children}
    </section>
  )
}

function BulletBlock({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <p className="rp-eyebrow">{label}</p>
      <p className="mt-2 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] p-3 text-sm leading-6">
        {text}
      </p>
    </div>
  )
}
