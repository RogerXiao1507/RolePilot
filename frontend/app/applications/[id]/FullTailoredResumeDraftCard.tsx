"use client"

import { useEffect, useState } from "react"
import {
  downloadTailoredResumeDocx,
  downloadTailoredResumePdf,
  getFullTailoredResumeDraft,
  getSavedFullResumeDraft,
  saveFullResumeDraft,
} from "@/lib/api"
import type {
  FullTailoredResumeDraft,
  SavedApplicationFullResumeDraft,
  SavedResume,
} from "@/lib/types"

type FullTailoredResumeDraftCardProps = {
  applicationId: number
  resume: SavedResume | null
}

export default function FullTailoredResumeDraftCard({
  applicationId,
  resume,
}: FullTailoredResumeDraftCardProps) {
  const [loading, setLoading] = useState(false)
  const [loadingSavedDraft, setLoadingSavedDraft] = useState(true)
  const [exportingDocx, setExportingDocx] = useState(false)
  const [exportingPdf, setExportingPdf] = useState(false)
  const [error, setError] = useState("")
  const [savedDraftMeta, setSavedDraftMeta] =
    useState<SavedApplicationFullResumeDraft | null>(null)
  const [result, setResult] = useState<FullTailoredResumeDraft | null>(null)

  useEffect(() => {
    async function loadData() {
      try {
        const savedDraft = await getSavedFullResumeDraft(applicationId)
        setSavedDraftMeta(savedDraft)
        setResult(savedDraft.draft_data)
      } catch (err) {
        console.error(err)
      } finally {
        setLoadingSavedDraft(false)
      }
    }

    loadData()
  }, [applicationId, resume?.id])

  async function handleGenerateFullDraft() {
    setLoading(true)
    setError("")

    try {
      if (!resume) {
        throw new Error("No saved resume found")
      }

      const data = await getFullTailoredResumeDraft(applicationId, resume.id)

      const saved = await saveFullResumeDraft({
        application_id: applicationId,
        resume_id: resume.id,
        draft_data: data,
      })

      setSavedDraftMeta(saved)
      setResult(data)
    } catch (err) {
      console.error(err)
      setError("Failed to generate full tailored resume draft.")
    } finally {
      setLoading(false)
    }
  }

  function triggerBrowserDownload(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  async function handleDownloadDocx() {
    setExportingDocx(true)
    setError("")

    try {
      const blob = await downloadTailoredResumeDocx(applicationId)
      triggerBrowserDownload(blob, `tailored_resume_app_${applicationId}.docx`)
    } catch (err) {
      console.error(err)
      setError("Failed to export DOCX.")
    } finally {
      setExportingDocx(false)
    }
  }

  async function handleDownloadPdf() {
    setExportingPdf(true)
    setError("")

    try {
      const blob = await downloadTailoredResumePdf(applicationId)
      triggerBrowserDownload(blob, `tailored_resume_app_${applicationId}.pdf`)
    } catch (err) {
      console.error(err)
      setError("Failed to export PDF.")
    } finally {
      setExportingPdf(false)
    }
  }

  return (
    <section className="rp-panel rp-section">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="rp-eyebrow">Export flow</p>
          <h2 className="rp-section-title mt-2">Full tailored resume draft</h2>
          <p className="rp-section-copy">
            Generate a full structured resume draft using the saved tailored content for this application.
          </p>
          {savedDraftMeta && (
            <p className="mt-2 text-xs text-[var(--muted)]">
              Last saved: {new Date(savedDraftMeta.updated_at).toLocaleString()}
            </p>
          )}
          {savedDraftMeta?.is_stale && (
            <p className="mt-2 text-xs font-bold text-amber-700">
              Stale — regenerate this draft before export.
            </p>
          )}
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleGenerateFullDraft}
            disabled={loading || !resume}
            className="rp-button-primary"
          >
            {loading ? "Generating..." : result ? "Refresh Full Draft" : "Generate Full Draft"}
          </button>

          {result && !savedDraftMeta?.is_stale && (
            <>
              <button
                onClick={handleDownloadDocx}
                disabled={exportingDocx}
                className="rp-button-secondary"
              >
                {exportingDocx ? "Downloading DOCX..." : "Download DOCX"}
              </button>

              <button
                onClick={handleDownloadPdf}
                disabled={exportingPdf}
                className="rp-button-secondary"
              >
                {exportingPdf ? "Downloading PDF..." : "Download PDF"}
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="rp-error mt-4">{error}</div>
      )}

      {loadingSavedDraft && !result && (
        <div className="mt-6 space-y-3">
          <div className="rp-skeleton h-5 w-1/3" />
          <div className="rp-skeleton h-24 w-full" />
          <div className="rp-skeleton h-24 w-full" />
        </div>
      )}

      {!result && !loading && !loadingSavedDraft && !error && (
        <div className="rp-empty mt-6">
          <p className="text-sm font-bold">No full draft yet</p>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
            Generate the full draft first, then you can download DOCX or PDF anytime.
          </p>
        </div>
      )}

      {result && !loading && (
        <div
          className="mt-6 overflow-x-auto rounded-lg border border-[var(--border)] bg-[#f1f3ee] p-3 shadow-sm sm:p-6"
        >
          <div
          className="mx-auto min-w-[720px] max-w-[900px] rounded-sm border border-zinc-200 bg-white p-14 text-black shadow-sm sm:p-20"
          style={{
            fontFamily: '"Times New Roman", Times, serif',
            lineHeight: 1.3,
          }}
        >
          <header className="pb-2 text-center">
            <h1 className="text-[30px] font-bold leading-none tracking-wide">
              {result.header.name}
            </h1>

            <p className="mt-2 text-[16px] leading-[1.3] text-zinc-700">
              {[
                result.header.location,
                result.header.phone,
                result.header.email,
                ...(result.header.websites || []),
              ]
                .filter(Boolean)
                .join(" | ")}
            </p>
          </header>

          <ResumeSection title="Education">
            <div className="space-y-4">
              {result.education.map((entry, index) => (
                <div key={index}>
                  <div className="flex flex-col justify-between gap-1 sm:flex-row sm:items-start">
                    <div>
                      <h3 className="text-[16px] font-semibold">{entry.school}</h3>
                      <p className="text-[16px] italic text-zinc-800">{entry.degree}</p>
                    </div>

                    <div className="text-[16px] italic text-zinc-700 sm:text-right">
                      {entry.date_range && <p className="font-bold not-italic">{entry.date_range}</p>}
                      {entry.location && <p>{entry.location}</p>}
                    </div>
                  </div>

                  {entry.gpa && (
                    <p className="mt-1 text-[16px] text-zinc-800">GPA: {entry.gpa}</p>
                  )}

                  {entry.coursework.length > 0 && (
                    <p className="mt-1 text-[16px] text-zinc-800">
                      <span className="font-bold">Coursework:</span>{" "}
                      {entry.coursework.join(", ")}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </ResumeSection>

          <ResumeSection title="Experience">
            <div className="space-y-5">
              {result.experience.map((entry, index) => (
                <ResumeBulletBlock key={index} entry={entry} />
              ))}
            </div>
          </ResumeSection>

          <ResumeSection title="Projects">
            <div className="space-y-5">
              {result.projects.map((entry, index) => (
                <ProjectBulletBlock key={index} entry={entry} />
              ))}
            </div>
          </ResumeSection>

          <ResumeSection title="Skills">
            <div className="space-y-2 text-[16px] leading-[1.35] text-zinc-800">
              {result.skills.programming_languages.length > 0 && (
                <p>
                  <span className="font-semibold">Programming Languages:</span>{" "}
                  {result.skills.programming_languages.join(", ")}
                </p>
              )}

              {result.skills.frameworks_tools.length > 0 && (
                <p>
                  <span className="font-semibold">Frameworks / Tools:</span>{" "}
                  {result.skills.frameworks_tools.join(", ")}
                </p>
              )}

              {result.skills.hardware_instrumentation.length > 0 && (
                <p>
                  <span className="font-semibold">Hardware / Instrumentation:</span>{" "}
                  {result.skills.hardware_instrumentation.join(", ")}
                </p>
              )}

              {result.skills.technical_areas.length > 0 && (
                <p>
                  <span className="font-semibold">Technical Areas:</span>{" "}
                  {result.skills.technical_areas.join(", ")}
                </p>
              )}

              {result.skills.developer_tools.length > 0 && (
                <p>
                  <span className="font-semibold">Developer Tools:</span>{" "}
                  {result.skills.developer_tools.join(", ")}
                </p>
              )}
            </div>
          </ResumeSection>
        </div>
        </div>
      )}
    </section>
  )
}

function ResumeSection({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <section className="mt-5">
      <h2 className="border-b-2 border-zinc-700 pb-1 text-[16px] font-bold uppercase tracking-wide text-zinc-900">
        {title}
      </h2>
      <div className="mt-3">{children}</div>
    </section>
  )
}

function ResumeBulletBlock({
  entry,
}: {
  entry: {
    title: string
    subtitle: string | null
    location: string | null
    date_range: string | null
    bullets: string[]
  }
}) {
  return (
    <div>
      <div className="flex flex-col justify-between gap-1 sm:flex-row sm:items-start">
        <div>
          <h3 className="text-[16px] font-semibold">{entry.title}</h3>
          {entry.subtitle && (
            <p className="text-[16px] italic text-zinc-800">{entry.subtitle}</p>
          )}
        </div>

        <div className="text-[16px] italic text-zinc-700 sm:text-right">
          {entry.date_range && <p className="font-bold not-italic">{entry.date_range}</p>}
          {entry.location && <p>{entry.location}</p>}
        </div>
      </div>

      {entry.bullets.length > 0 && (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-[16px] leading-[1.35] text-zinc-800">
          {entry.bullets.map((bullet, index) => (
            <li key={index}>{bullet}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function ProjectBulletBlock({
  entry,
}: {
  entry: {
    title: string
    subtitle?: string | null
    location: string | null
    date_range: string | null
    bullets: string[]
  }
}) {
  return (
    <div>
      <div className="flex flex-col justify-between gap-1 sm:flex-row sm:items-start">
        <div>
          <h3 className="text-[16px] font-semibold">{entry.title}</h3>
        </div>

        <div className="text-[16px] italic text-zinc-700 sm:text-right">
          {entry.date_range && <p className="font-bold not-italic">{entry.date_range}</p>}
          {entry.location && <p>{entry.location}</p>}
        </div>
      </div>

      {entry.bullets.length > 0 && (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-[16px] leading-[1.35] text-zinc-800">
          {entry.bullets.map((bullet, index) => (
            <li key={index}>{bullet}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
