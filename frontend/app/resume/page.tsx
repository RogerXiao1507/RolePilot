"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { analyzeResume, getLatestResume, saveResume } from "@/lib/api"
import type { ResumeAnalysis, SavedResume } from "@/lib/types"
import AccountMenu from "@/components/AccountMenu"

export default function ResumePage() {
  const [file, setFile] = useState<File | null>(null)
  const [savedResume, setSavedResume] = useState<SavedResume | null>(null)
  const [result, setResult] = useState<ResumeAnalysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingSavedResume, setLoadingSavedResume] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    async function loadLatestResume() {
      try {
        const resume = await getLatestResume()

        setSavedResume(resume)
        setResult({
          summary: resume.summary,
          strengths: resume.strengths,
          weaknesses: resume.weaknesses,
          wording_issues: resume.wording_issues,
          missing_metrics: resume.missing_metrics,
          suggested_improvements: resume.suggested_improvements,
          extracted_text: resume.extracted_text,
        })
      } catch (err) {
        console.error(err)
      } finally {
        setLoadingSavedResume(false)
      }
    }

    loadLatestResume()
  }, [])

  async function handleAnalyze() {
    if (!file) {
      setError("Select a PDF resume before running analysis.")
      return
    }

    setLoading(true)
    setError("")

    try {
      const analysis = await analyzeResume(file)

      const saved = await saveResume({
        file_name: file.name,
        extracted_text: analysis.extracted_text,
        summary: analysis.summary,
        strengths: analysis.strengths,
        weaknesses: analysis.weaknesses,
        wording_issues: analysis.wording_issues,
        missing_metrics: analysis.missing_metrics,
        suggested_improvements: analysis.suggested_improvements,
      })

      setSavedResume(saved)
      setResult(analysis)
    } catch (err) {
      console.error(err)
      setError("Resume analysis failed. Keep the selected PDF and try again.")
    } finally {
      setLoading(false)
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selectedFile = e.target.files?.[0] || null

    if (!selectedFile) {
      setFile(null)
      return
    }

    if (selectedFile.type !== "application/pdf") {
      setError("Only PDF files are allowed.")
      setFile(null)
      return
    }

    setError("")
    setFile(selectedFile)
  }

  const displayedFileName =
    file?.name || savedResume?.file_name || "No file selected"

  return (
    <main className="rp-page">
      <div className="rp-shell-wide">
        <nav className="rp-topbar" aria-label="Primary navigation">
          <Link href="/applications" className="rp-brand">
            <span className="rp-brand-mark">RP</span>
            <span>RolePilot</span>
          </Link>

          <div className="rp-nav">
            <Link href="/applications" className="rp-nav-link">
              Dashboard
            </Link>
            <Link href="/applications/new" className="rp-button-primary">
              Add Application
            </Link>
            <AccountMenu />
          </div>
        </nav>

        <section className="rp-header rp-header-grid">
          <div>
            <p className="rp-eyebrow">Resume intelligence</p>
            <h1 className="rp-title">Review your resume before every application.</h1>
            <p className="rp-subtitle">
              Upload a PDF, save structured feedback, and reuse the latest resume for
              application matching and tailored draft generation.
            </p>
          </div>

          <div className="rp-panel-strong rp-section">
            <p className="rp-eyebrow text-zinc-300">Current resume</p>
            <p className="mt-4 text-lg font-semibold">{displayedFileName}</p>
            <div className="mt-6 grid grid-cols-2 gap-4 border-t border-white/10 pt-5">
              <Snapshot label="Strengths" value={result?.strengths.length ?? 0} />
              <Snapshot label="Fixes" value={(result?.weaknesses.length ?? 0) + (result?.wording_issues.length ?? 0)} />
            </div>
          </div>
        </section>

        <div className="grid gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="space-y-4">
            <section className="rp-panel rp-section">
              <p className="rp-eyebrow">Upload</p>
              <h2 className="rp-section-title mt-2">Resume PDF</h2>
              <p className="rp-section-copy">
                Select a PDF file and generate structured AI feedback.
              </p>

              <label htmlFor="resume-upload" className="rp-field-label mt-5">
                PDF file
              </label>
              <input
                id="resume-upload"
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="block w-full cursor-pointer rounded-lg border border-[var(--border)] bg-white p-2 text-sm text-[var(--muted)] file:mr-4 file:rounded-md file:border-0 file:bg-[var(--surface-strong)] file:px-4 file:py-2 file:text-sm file:font-bold file:text-white hover:bg-[var(--surface-muted)]"
              />

              <div className="mt-4 rounded-lg border border-[var(--border)] bg-white p-4">
                <p className="rp-eyebrow">Selected file</p>
                <p className="mt-2 break-words text-sm font-semibold">{displayedFileName}</p>

                {!file && savedResume && (
                  <p className="mt-2 text-xs leading-5 text-[var(--muted)]">
                    Latest saved resume loaded from the database.
                  </p>
                )}
              </div>

              {savedResume && (
                <div className="mt-4 rounded-lg border border-[var(--border)] bg-white p-4">
                  <p className="rp-eyebrow">Saved resume ID</p>
                  <p className="mt-2 font-mono text-sm font-bold">{savedResume.id}</p>
                </div>
              )}

              {error && <div className="rp-error mt-4">{error}</div>}

              <button
                onClick={handleAnalyze}
                disabled={loading || !file}
                className="rp-button-primary mt-5 w-full"
              >
                {loading ? "Analyzing Resume..." : "Analyze Resume"}
              </button>
            </section>

            <section className="rp-panel overflow-hidden">
              <div className="grid grid-cols-2">
                <StatCard label="Strengths" value={result ? String(result.strengths.length) : "-"} />
                <StatCard label="Weaknesses" value={result ? String(result.weaknesses.length) : "-"} />
                <StatCard label="Wording" value={result ? String(result.wording_issues.length) : "-"} />
                <StatCard label="Metrics" value={result ? String(result.missing_metrics.length) : "-"} />
              </div>
            </section>
          </aside>

          <section className="space-y-4">
            {loadingSavedResume && !result && (
              <div className="rp-panel rp-section">
                <p className="rp-eyebrow">Loading</p>
                <h2 className="rp-section-title mt-2">Fetching saved resume</h2>
                <div className="mt-6 space-y-3">
                  <div className="rp-skeleton h-5 w-3/4" />
                  <div className="rp-skeleton h-5 w-full" />
                  <div className="rp-skeleton h-5 w-2/3" />
                </div>
              </div>
            )}

            {!loadingSavedResume && !result && !loading && (
              <div className="rp-empty">
                <p className="rp-section-title">No analysis yet</p>
                <p className="rp-section-copy">
                  Upload a PDF resume and run analysis to see strengths, gaps,
                  wording issues, and suggested improvements.
                </p>
              </div>
            )}

            {loading && (
              <div className="rp-panel rp-section">
                <p className="rp-eyebrow">Analysis running</p>
                <h2 className="rp-section-title mt-2">Extracting feedback</h2>
                <p className="rp-section-copy">
                  RolePilot is extracting text, generating feedback, and saving the resume.
                </p>

                <div className="mt-6 grid gap-3 md:grid-cols-2">
                  <div className="rp-skeleton h-28" />
                  <div className="rp-skeleton h-28" />
                  <div className="rp-skeleton h-28" />
                  <div className="rp-skeleton h-28" />
                </div>
              </div>
            )}

            {result && !loading && (
              <>
                <SectionCard title="Summary">
                  <p className="text-sm leading-7 text-[var(--foreground)]">{result.summary}</p>
                </SectionCard>

                <div className="grid gap-4 md:grid-cols-2">
                  <AnalysisCard title="Strengths" items={result.strengths} tone="accent" />
                  <AnalysisCard title="Weaknesses" items={result.weaknesses} tone="danger" />
                  <AnalysisCard title="Wording Issues" items={result.wording_issues} tone="warning" />
                  <AnalysisCard title="Missing Metrics" items={result.missing_metrics} tone="info" />
                </div>

                <AnalysisCard
                  title="Suggested Improvements"
                  items={result.suggested_improvements}
                  tone="neutral"
                />

                <details className="rp-panel rp-section">
                  <summary className="cursor-pointer text-lg font-bold">
                    Extracted Text
                  </summary>
                  <p className="rp-section-copy">
                    Useful for debugging PDF extraction and analysis quality.
                  </p>
                  <div className="mt-4 max-h-96 overflow-y-auto rounded-lg border border-[var(--border)] bg-white p-4 whitespace-pre-wrap text-sm leading-7 text-[var(--foreground)]">
                    {result.extracted_text}
                  </div>
                </details>
              </>
            )}
          </section>
        </div>
      </div>
    </main>
  )
}

function Snapshot({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="font-mono text-3xl font-bold tracking-[-0.05em]">{value}</p>
      <p className="mt-1 text-xs text-zinc-300">{label}</p>
    </div>
  )
}

function StatCard({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="border-b border-r border-[var(--border)] p-4 odd:border-l-0 even:border-r-0">
      <p className="rp-metric-label">{label}</p>
      <p className="mt-2 font-mono text-2xl font-bold tracking-[-0.04em]">{value}</p>
    </div>
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
    <section className="rp-panel rp-section">
      <h2 className="rp-section-title mb-4">{title}</h2>
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
    <section className="rp-panel rp-section">
      <h2 className="rp-section-title mb-4">{title}</h2>

      {items.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">No items found.</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item, index) => (
            <li
              key={`${item}-${index}`}
              className={`rounded-lg border p-4 text-sm leading-6 ${toneClasses[tone]}`}
            >
              {item}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
