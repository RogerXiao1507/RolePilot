"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState } from "react"

import { updateApplication } from "@/lib/api"
import type { ResumeListItem } from "@/lib/types"

type Props = {
  applicationId: number
  resumes: ResumeListItem[]
  selectedResumeId: number | null
}

export default function ApplicationResumeSelector({
  applicationId,
  resumes,
  selectedResumeId,
}: Props) {
  const router = useRouter()
  const [value, setValue] = useState(selectedResumeId ? String(selectedResumeId) : "")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  async function handleChange(event: React.ChangeEvent<HTMLSelectElement>) {
    const nextValue = event.target.value
    setValue(nextValue)
    setSaving(true)
    setError("")
    try {
      await updateApplication(applicationId, {
        selected_resume_id: nextValue ? Number(nextValue) : null,
      })
      router.refresh()
    } catch (err) {
      console.error(err)
      setValue(selectedResumeId ? String(selectedResumeId) : "")
      setError("Could not change the selected resume.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="rp-panel rp-section">
      <p className="rp-eyebrow">Application resume</p>
      <h2 className="rp-section-title mt-2">Source of truth</h2>
      <p className="rp-section-copy">
        Match, tailoring, and full-draft generation use this resume only.
      </p>

      {resumes.length > 0 ? (
        <>
          <label htmlFor="application-resume" className="rp-field-label mt-4">
            Selected resume
          </label>
          <select
            id="application-resume"
            value={value}
            onChange={handleChange}
            disabled={saving}
            className="rp-input"
          >
            <option value="">No resume selected</option>
            {resumes.map((resume) => (
              <option key={resume.id} value={resume.id}>
                {resume.label}{resume.is_default ? " (default)" : ""}
              </option>
            ))}
          </select>
          {saving && <p className="mt-2 text-xs text-[var(--muted)]">Saving selection…</p>}
          {error && <div className="rp-error mt-3">{error}</div>}
        </>
      ) : (
        <div className="rp-empty mt-4">
          <p className="text-sm font-bold">No resume available</p>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Upload a resume before running a match.
          </p>
        </div>
      )}

      <Link href="/resume" className="rp-button-secondary mt-4 w-full">
        Manage Resumes
      </Link>
    </section>
  )
}
