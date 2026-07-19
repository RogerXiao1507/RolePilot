"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

import AccountMenu from "@/components/AccountMenu"
import {
  createProjectEvidence,
  confirmProjectEvidenceMetric,
  deleteProjectEvidence,
  getProjectEvidence,
  retryProjectEvidence,
  updateProjectEvidence,
} from "@/lib/api"
import type {
  EvidenceMetric,
  ProjectEvidence,
  ProjectEvidenceInput,
} from "@/lib/types"

type FormState = {
  title: string
  category: string
  description: string
  outcome: string
  startDate: string
  endDate: string
  skills: string
  keywords: string
  links: string
  bullets: string
  metrics: string
}

const EMPTY_FORM: FormState = {
  title: "",
  category: "project",
  description: "",
  outcome: "",
  startDate: "",
  endDate: "",
  skills: "",
  keywords: "",
  links: "",
  bullets: "",
  metrics: "",
}

function lines(value: string): string[] {
  return value.split(/\n|,/).map((item) => item.trim()).filter(Boolean)
}

function parseMetrics(value: string): EvidenceMetric[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [label, metricValue, ...contextParts] = line.split("|").map((part) => part.trim())
      return {
        label: label || "Metric",
        value: metricValue || label,
        context: contextParts.join(" | ") || null,
      }
    })
}

export default function EvidencePage() {
  const [items, setItems] = useState<ProjectEvidence[]>([])
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  async function refresh() {
    setItems(await getProjectEvidence())
  }

  useEffect(() => {
    refresh()
      .catch((err) => {
        console.error(err)
        setError("Could not load your evidence library.")
      })
      .finally(() => setLoading(false))
  }, [])

  function payloadFromForm(): ProjectEvidenceInput {
    return {
      title: form.title,
      category: form.category,
      description: form.description,
      outcome: form.outcome || null,
      start_date: form.startDate || null,
      end_date: form.endDate || null,
      skills: lines(form.skills),
      keywords: lines(form.keywords),
      links: lines(form.links),
      bullet_bank: form.bullets.split("\n").map((item) => item.trim()).filter(Boolean),
      verified_metrics: parseMetrics(form.metrics),
    }
  }

  async function handleSave(event: React.FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError("")
    try {
      const payload = payloadFromForm()
      if (editingId) {
        await updateProjectEvidence(editingId, payload)
      } else {
        await createProjectEvidence(payload)
      }
      setForm(EMPTY_FORM)
      setEditingId(null)
      await refresh()
    } catch (err) {
      console.error(err)
      setError("Evidence could not be saved. Your form values are preserved.")
    } finally {
      setSaving(false)
    }
  }

  function edit(item: ProjectEvidence) {
    setEditingId(item.id)
    setForm({
      title: item.title,
      category: item.category,
      description: item.description,
      outcome: item.outcome || "",
      startDate: item.start_date || "",
      endDate: item.end_date || "",
      skills: item.skills.join(", "),
      keywords: item.keywords.join(", "),
      links: item.links.join("\n"),
      bullets: item.bullet_bank.join("\n"),
      metrics: item.verified_metrics
        .map((metric) => [metric.label, metric.value, metric.context].filter(Boolean).join(" | "))
        .join("\n"),
    })
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  async function remove(id: number) {
    if (!window.confirm("Delete this evidence and its retrieval chunks?")) return
    try {
      await deleteProjectEvidence(id)
      if (editingId === id) {
        setEditingId(null)
        setForm(EMPTY_FORM)
      }
      await refresh()
    } catch (err) {
      console.error(err)
      setError("Evidence could not be deleted.")
    }
  }

  async function retry(id: number) {
    try {
      await retryProjectEvidence(id)
      await refresh()
    } catch (err) {
      console.error(err)
      setError("Evidence ingestion could not be retried.")
    }
  }

  async function confirmMetric(id: number, suggestionIndex: number) {
    try {
      await confirmProjectEvidenceMetric(id, suggestionIndex)
      await refresh()
    } catch (err) {
      console.error(err)
      setError("The suggested metric could not be confirmed.")
    }
  }

  return (
    <main className="rp-page">
      <div className="rp-shell-wide">
        <nav className="rp-topbar" aria-label="Primary navigation">
          <Link href="/applications" className="rp-brand">
            <span className="rp-brand-mark">RP</span>
            <span>RolePilot</span>
          </Link>
          <div className="rp-nav">
            <Link href="/applications" className="rp-nav-link">Dashboard</Link>
            <Link href="/resume" className="rp-nav-link">Resumes</Link>
            <AccountMenu />
          </div>
        </nav>

        <section className="rp-header rp-header-grid">
          <div>
            <p className="rp-eyebrow">Evidence library</p>
            <h1 className="rp-title">Keep every tailored claim grounded.</h1>
            <p className="rp-subtitle">
              Save projects, outcomes, verified metrics, skills, and links that RolePilot may retrieve during tailoring.
            </p>
          </div>
          <div className="rp-panel-strong rp-section">
            <p className="rp-eyebrow text-zinc-300">Retrieval readiness</p>
            <div className="mt-5 grid grid-cols-3 gap-3">
              <Metric label="Ready" value={items.filter((item) => item.ingestion_status === "ready").length} />
              <Metric label="Pending" value={items.filter((item) => item.ingestion_status === "pending").length} />
              <Metric label="Failed" value={items.filter((item) => item.ingestion_status === "failed").length} />
            </div>
          </div>
        </section>

        {error && <div className="rp-error mb-4">{error}</div>}

        <div className="grid gap-4 lg:grid-cols-[420px_minmax(0,1fr)]">
          <form onSubmit={handleSave} className="rp-panel rp-section space-y-4 lg:sticky lg:top-5 lg:self-start">
            <div>
              <p className="rp-eyebrow">{editingId ? "Edit source" : "Add source"}</p>
              <h2 className="rp-section-title mt-2">Guided evidence form</h2>
            </div>
            <Field label="Title" required value={form.title} onChange={(value) => setForm({ ...form, title: value })} />
            <Field label="Category" required value={form.category} onChange={(value) => setForm({ ...form, category: value })} />
            <TextArea label="What did you do?" required value={form.description} onChange={(value) => setForm({ ...form, description: value })} />
            <TextArea label="Outcome" value={form.outcome} onChange={(value) => setForm({ ...form, outcome: value })} />
            <div className="grid grid-cols-2 gap-3">
              <Field label="Start date" value={form.startDate} onChange={(value) => setForm({ ...form, startDate: value })} />
              <Field label="End date" value={form.endDate} onChange={(value) => setForm({ ...form, endDate: value })} />
            </div>
            <Field label="Skills (comma separated)" value={form.skills} onChange={(value) => setForm({ ...form, skills: value })} />
            <Field label="Keywords (comma separated)" value={form.keywords} onChange={(value) => setForm({ ...form, keywords: value })} />
            <TextArea label="Resume bullets (one per line)" value={form.bullets} onChange={(value) => setForm({ ...form, bullets: value })} />
            <TextArea label="Verified metrics (Label | Value | Context)" value={form.metrics} onChange={(value) => setForm({ ...form, metrics: value })} />
            <TextArea label="Links (one per line)" value={form.links} onChange={(value) => setForm({ ...form, links: value })} />
            <div className="flex gap-3">
              <button type="submit" disabled={saving} className="rp-button-primary flex-1">
                {saving ? "Saving…" : editingId ? "Save Changes" : "Add Evidence"}
              </button>
              {editingId && (
                <button type="button" className="rp-button-secondary" onClick={() => { setEditingId(null); setForm(EMPTY_FORM) }}>
                  Cancel
                </button>
              )}
            </div>
          </form>

          <section className="space-y-4">
            {loading && <div className="rp-panel rp-section"><div className="rp-skeleton h-28" /></div>}
            {!loading && items.length === 0 && (
              <div className="rp-empty">
                <p className="rp-section-title">No evidence yet</p>
                <p className="rp-section-copy">Add a project or accomplishment to create your retrieval library.</p>
              </div>
            )}
            {items.map((item) => (
              <article key={item.id} className="rp-panel rp-section">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex flex-wrap gap-2">
                      <span className="rp-badge">{item.category}</span>
                      <StatusBadge status={item.ingestion_status} />
                      <span className="rp-badge">v{item.version}</span>
                    </div>
                    <h2 className="rp-section-title mt-3">{item.title}</h2>
                    <p className="rp-section-copy">{item.description}</p>
                  </div>
                  <div className="flex gap-3 text-xs font-bold">
                    <button onClick={() => edit(item)} className="text-[var(--accent-strong)]">Edit</button>
                    <button onClick={() => remove(item.id)} className="text-red-700">Delete</button>
                  </div>
                </div>

                {item.outcome && <p className="mt-4 rounded-lg border border-[var(--border)] bg-white p-4 text-sm"><strong>Outcome:</strong> {item.outcome}</p>}
                <div className="mt-4 flex flex-wrap gap-2">
                  {item.skills.map((skill) => <span key={skill} className="rp-badge border-blue-200 bg-blue-50 text-blue-700">{skill}</span>)}
                  {item.verified_metrics.map((metric, index) => <span key={`${metric.label}-${index}`} className="rp-badge border-emerald-200 bg-emerald-50 text-emerald-800">✓ {metric.label}: {metric.value}</span>)}
                </div>
                {item.ai_suggested_metrics.length > 0 && (
                  <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
                    <p className="text-xs font-bold text-amber-900">AI suggestions — not used until you confirm them</p>
                    <div className="mt-3 space-y-2">
                      {item.ai_suggested_metrics.map((metric, index) => (
                        <div key={`${metric.label}-${metric.value}-${index}`} className="flex flex-wrap items-center justify-between gap-3 text-sm">
                          <span>{metric.label}: {metric.value}{metric.context ? ` · ${metric.context}` : ""}</span>
                          <button onClick={() => confirmMetric(item.id, index)} className="text-xs font-bold text-amber-900 underline">
                            Confirm as user-verified
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {item.ingestion_status === "failed" && (
                  <div className="rp-error mt-4">
                    <p>{item.ingestion_error}</p>
                    <button onClick={() => retry(item.id)} className="mt-2 text-xs font-bold underline">Retry ingestion</button>
                  </div>
                )}
              </article>
            ))}
          </section>
        </div>
      </div>
    </main>
  )
}

function Field({ label, value, onChange, required = false }: { label: string; value: string; onChange: (value: string) => void; required?: boolean }) {
  return <label className="block"><span className="rp-field-label">{label}</span><input required={required} value={value} onChange={(event) => onChange(event.target.value)} className="rp-input" /></label>
}

function TextArea({ label, value, onChange, required = false }: { label: string; value: string; onChange: (value: string) => void; required?: boolean }) {
  return <label className="block"><span className="rp-field-label">{label}</span><textarea required={required} value={value} onChange={(event) => onChange(event.target.value)} rows={3} className="rp-input min-h-24" /></label>
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div><p className="font-mono text-3xl font-bold">{value}</p><p className="mt-1 text-xs text-zinc-300">{label}</p></div>
}

function StatusBadge({ status }: { status: ProjectEvidence["ingestion_status"] }) {
  const classes = status === "ready" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : status === "failed" ? "border-red-200 bg-red-50 text-red-700" : "border-amber-200 bg-amber-50 text-amber-800"
  return <span className={`rp-badge ${classes}`}>{status}</span>
}
