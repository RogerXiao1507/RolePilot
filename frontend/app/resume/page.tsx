"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { analyzeResume, getLatestResume, saveResume } from "@/lib/api"
import type { ResumeAnalysis, SavedResume } from "@/lib/types"

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
      setError("Please select a PDF resume first.")
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
      setError("Failed to analyze and save resume.")
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
    file?.name || savedResume?.file_name || "No file chosen"

  return (
    <main className="min-h-screen bg-[#0a0a0b] px-6 py-10 text-zinc-100">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex flex-col gap-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-5xl font-bold tracking-tight text-white">
                Resume Analyzer
              </h1>
              <p className="mt-2 text-sm text-zinc-400">
                Upload your resume and get AI feedback on strengths, weaknesses,
                wording, and improvements.
              </p>
            </div>

            <Link
              href="/applications"
              className="rounded-xl border border-zinc-800 bg-zinc-900 px-5 py-3 text-sm font-medium text-zinc-200 transition hover:border-zinc-700 hover:bg-zinc-800"
            >
              Back to Applications
            </Link>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <section className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-6 shadow-sm lg:col-span-1">
            <h2 className="text-xl font-semibold text-white">Upload Resume PDF</h2>
            <p className="mt-2 text-sm text-zinc-400">
              Select a PDF file and generate structured AI feedback.
            </p>

            <div className="mt-6">
              <input
                id="resume-upload"
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="block w-full text-sm text-zinc-300 file:mr-4 file:rounded-xl file:border file:border-emerald-700 file:bg-emerald-600 file:px-4 file:py-3 file:text-sm file:font-medium file:text-white hover:file:bg-emerald-500"
              />
            </div>

            <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
              <p className="text-xs uppercase tracking-wide text-zinc-500">
                Current resume
              </p>
              <p className="mt-2 text-sm text-zinc-200">{displayedFileName}</p>

              {!file && savedResume && (
                <p className="mt-2 text-xs text-zinc-500">
                  Latest saved resume loaded from the database.
                </p>
              )}
            </div>

            {savedResume && (
              <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
                <p className="text-xs uppercase tracking-wide text-zinc-500">
                  Saved Resume ID
                </p>
                <p className="mt-2 text-sm text-zinc-200">{savedResume.id}</p>
              </div>
            )}

            {error && (
              <div className="mt-4 rounded-xl border border-red-800 bg-red-950/50 p-4 text-sm text-red-300">
                {error}
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={loading || !file}
              className="mt-6 w-full rounded-xl border border-emerald-700 bg-emerald-600 px-5 py-3 text-sm font-medium text-white transition hover:border-emerald-600 hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Analyzing..." : "Analyze Resume"}
            </button>

            <div className="mt-6 grid grid-cols-2 gap-4">
              <StatCard
                label="Strengths"
                value={result ? String(result.strengths.length) : "—"}
              />
              <StatCard
                label="Weaknesses"
                value={result ? String(result.weaknesses.length) : "—"}
              />
              <StatCard
                label="Wording"
                value={result ? String(result.wording_issues.length) : "—"}
              />
              <StatCard
                label="Metrics"
                value={result ? String(result.missing_metrics.length) : "—"}
              />
            </div>
          </section>

          <div className="lg:col-span-2">
            {loadingSavedResume && !result && (
              <section className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-8 shadow-sm">
                <h2 className="text-2xl font-semibold text-white">Loading saved resume...</h2>
                <p className="mt-3 text-zinc-400">
                  Fetching your latest saved resume from the database.
                </p>
              </section>
            )}

            {!loadingSavedResume && !result && !loading && (
              <section className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-8 shadow-sm">
                <h2 className="text-2xl font-semibold text-white">No analysis yet</h2>
                <p className="mt-3 text-zinc-400">
                  Upload a PDF resume and click Analyze Resume to see the results here.
                </p>
              </section>
            )}

            {loading && (
              <section className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-8 shadow-sm">
                <h2 className="text-2xl font-semibold text-white">Analyzing resume...</h2>
                <p className="mt-3 text-zinc-400">
                  Extracting text, generating feedback, and saving to the database.
                </p>

                <div className="mt-6 space-y-3">
                  <div className="h-4 animate-pulse rounded bg-zinc-800" />
                  <div className="h-4 animate-pulse rounded bg-zinc-800" />
                  <div className="h-4 w-2/3 animate-pulse rounded bg-zinc-800" />
                </div>
              </section>
            )}

            {result && !loading && (
              <div className="space-y-6">
                <SectionCard title="Summary">
                  <p className="text-base leading-8 text-zinc-200">{result.summary}</p>
                </SectionCard>

                <div className="grid gap-6 md:grid-cols-2">
                  <AnalysisCard title="Strengths" items={result.strengths} />
                  <AnalysisCard title="Weaknesses" items={result.weaknesses} />
                  <AnalysisCard title="Wording Issues" items={result.wording_issues} />
                  <AnalysisCard title="Missing Metrics" items={result.missing_metrics} />
                </div>

                <AnalysisCard
                  title="Suggested Improvements"
                  items={result.suggested_improvements}
                />

                <details className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-6 shadow-sm">
                  <summary className="cursor-pointer text-xl font-semibold text-white">
                    Extracted Text
                  </summary>
                  <p className="mt-2 text-sm text-zinc-400">
                    Useful for debugging PDF extraction and analysis quality.
                  </p>
                  <div className="mt-4 max-h-96 overflow-y-auto rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 text-sm leading-7 text-zinc-300 whitespace-pre-wrap">
                    {result.extracted_text}
                  </div>
                </details>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
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
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4 shadow-sm">
      <p className="text-sm text-zinc-400">{label}</p>
      <p className="mt-2 text-2xl font-bold text-white">{value}</p>
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
    <section className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-6 shadow-sm">
      <h2 className="mb-4 text-2xl font-semibold text-white">{title}</h2>
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
    <section className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-6 shadow-sm">
      <h2 className="mb-4 text-2xl font-semibold text-white">{title}</h2>

      {items.length === 0 ? (
        <p className="text-zinc-500">No items found.</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item, index) => (
            <li
              key={index}
              className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 text-zinc-200"
            >
              {item}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}