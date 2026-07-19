"use client"

import Link from "next/link"
import { useCallback, useEffect, useMemo, useState } from "react"

import AppTopbar from "@/components/AppTopbar"
import {
  clearDiscoveryAction,
  convertDiscoveryJob,
  createJobSearch,
  deleteJobSearch,
  getDiscoveryCatalogStatus,
  getDiscoveryFeed,
  getJobSearches,
  getResumes,
  setDiscoveryAction,
  updateJobSearch,
} from "@/lib/api"
import type {
  DiscoveryActionState,
  DiscoveryCatalogStatus,
  DiscoveryJob,
  JobRecency,
  JobSearch,
  JobSearchInput,
  JobSort,
  ResumeListItem,
} from "@/lib/types"

type SearchForm = Omit<JobSearchInput,
  "target_titles" | "adjacent_titles" | "seniority_levels" | "employment_types" |
  "locations" | "workplace_types" | "industries" | "required_keywords" |
  "excluded_keywords" | "excluded_companies"
> & {
  target_titles: string
  adjacent_titles: string
  seniority_levels: string
  employment_types: string
  locations: string
  workplace_types: string
  industries: string
  required_keywords: string
  excluded_keywords: string
  excluded_companies: string
}

const EMPTY_FORM: SearchForm = {
  name: "",
  resume_id: null,
  target_titles: "",
  adjacent_titles: "",
  seniority_levels: "",
  employment_types: "Internship",
  locations: "",
  workplace_types: "Remote, Hybrid",
  salary_min: null,
  salary_max: null,
  salary_currency: "USD",
  industries: "",
  required_keywords: "",
  excluded_keywords: "",
  excluded_companies: "",
  recency: "7d",
  notification_frequency: "off",
  is_active: true,
}

const RECENCY_OPTIONS: Array<[JobRecency, string]> = [
  ["24h", "Last 24 hours"], ["7d", "Last 7 days"], ["14d", "Last 14 days"],
  ["30d", "Last 30 days"], ["all", "All active"],
]

const SORT_OPTIONS: Array<[JobSort, string]> = [
  ["recommended", "Recommended"], ["newest", "Newest"],
  ["most_relevant", "Most relevant"],
]

function list(value: string): string[] {
  return value.split(/,|\n/).map((item) => item.trim()).filter(Boolean)
}

function toPayload(form: SearchForm): JobSearchInput {
  return {
    ...form,
    target_titles: list(form.target_titles),
    adjacent_titles: list(form.adjacent_titles),
    seniority_levels: list(form.seniority_levels),
    employment_types: list(form.employment_types),
    locations: list(form.locations),
    workplace_types: list(form.workplace_types),
    industries: list(form.industries),
    required_keywords: list(form.required_keywords),
    excluded_keywords: list(form.excluded_keywords),
    excluded_companies: list(form.excluded_companies),
  }
}

function toForm(search: JobSearch): SearchForm {
  return {
    ...search,
    target_titles: search.target_titles.join(", "),
    adjacent_titles: search.adjacent_titles.join(", "),
    seniority_levels: search.seniority_levels.join(", "),
    employment_types: search.employment_types.join(", "),
    locations: search.locations.join(", "),
    workplace_types: search.workplace_types.join(", "),
    industries: search.industries.join(", "),
    required_keywords: search.required_keywords.join(", "),
    excluded_keywords: search.excluded_keywords.join(", "),
    excluded_companies: search.excluded_companies.join(", "),
  }
}

export default function DiscoverPage() {
  const [searches, setSearches] = useState<JobSearch[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [form, setForm] = useState<SearchForm>(EMPTY_FORM)
  const [resumes, setResumes] = useState<ResumeListItem[]>([])
  const [jobs, setJobs] = useState<DiscoveryJob[]>([])
  const [catalog, setCatalog] = useState<DiscoveryCatalogStatus | null>(null)
  const [recency, setRecency] = useState<JobRecency>("7d")
  const [sort, setSort] = useState<JobSort>("recommended")
  const [loading, setLoading] = useState(true)
  const [loadingFeed, setLoadingFeed] = useState(false)
  const [saving, setSaving] = useState(false)
  const [workingJob, setWorkingJob] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState("")

  const selected = useMemo(
    () => searches.find((search) => search.id === selectedId) ?? null,
    [searches, selectedId]
  )

  const loadFeed = useCallback(async (searchId: string, nextRecency: JobRecency, nextSort: JobSort) => {
    setLoadingFeed(true)
    setError("")
    try {
      const result = await getDiscoveryFeed({ searchId, recency: nextRecency, sort: nextSort })
      setJobs(result.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load discovered jobs.")
    } finally {
      setLoadingFeed(false)
    }
  }, [])

  useEffect(() => {
    Promise.all([getJobSearches(), getResumes(), getDiscoveryCatalogStatus()])
      .then(([savedSearches, savedResumes, catalogStatus]) => {
        setSearches(savedSearches)
        setResumes(savedResumes)
        setCatalog(catalogStatus)
        const first = savedSearches[0]
        if (first) {
          setSelectedId(first.id)
          setRecency(first.recency)
          void loadFeed(first.id, first.recency, "recommended")
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Discovery could not load."))
      .finally(() => setLoading(false))
  }, [loadFeed])

  function selectSearch(search: JobSearch) {
    setSelectedId(search.id)
    setEditing(false)
    setRecency(search.recency)
    setSort("recommended")
    void loadFeed(search.id, search.recency, "recommended")
  }

  function beginNew() {
    setSelectedId(null)
    setForm({ ...EMPTY_FORM, resume_id: resumes.find((resume) => resume.is_default)?.id ?? null })
    setJobs([])
    setEditing(true)
  }

  function beginEdit() {
    if (!selected) return
    setForm(toForm(selected))
    setEditing(true)
  }

  async function saveSearch(event: React.FormEvent) {
    event.preventDefault()
    const payload = toPayload(form)
    if (!payload.target_titles.length) {
      setError("Add at least one target title.")
      return
    }
    setSaving(true)
    setError("")
    try {
      const saved = selectedId
        ? await updateJobSearch(selectedId, payload)
        : await createJobSearch(payload)
      const next = selectedId
        ? searches.map((item) => item.id === saved.id ? saved : item)
        : [saved, ...searches]
      setSearches(next)
      setSelectedId(saved.id)
      setRecency(saved.recency)
      setEditing(false)
      await loadFeed(saved.id, saved.recency, sort)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save that search.")
    } finally {
      setSaving(false)
    }
  }

  async function removeSearch() {
    if (!selected || !window.confirm(`Delete “${selected.name}”?`)) return
    try {
      await deleteJobSearch(selected.id)
      const next = searches.filter((item) => item.id !== selected.id)
      setSearches(next)
      setEditing(false)
      setJobs([])
      const first = next[0]
      setSelectedId(first?.id ?? null)
      if (first) void loadFeed(first.id, first.recency, "recommended")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete that search.")
    }
  }

  async function action(job: DiscoveryJob, state: Exclude<DiscoveryActionState, "converted">) {
    setWorkingJob(job.id)
    setError("")
    try {
      if (job.action_state === state) await clearDiscoveryAction(job.id)
      else await setDiscoveryAction(job.id, state)
      if (selectedId) await loadFeed(selectedId, recency, sort)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update that job.")
    } finally {
      setWorkingJob(null)
    }
  }

  async function hideCompany(job: DiscoveryJob) {
    if (!selected) return
    setWorkingJob(job.id)
    try {
      const excluded = Array.from(new Set([...selected.excluded_companies, job.company_name]))
      const saved = await updateJobSearch(selected.id, { excluded_companies: excluded })
      setSearches(searches.map((item) => item.id === saved.id ? saved : item))
      await loadFeed(saved.id, recency, sort)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not hide that company.")
    } finally {
      setWorkingJob(null)
    }
  }

  async function convert(job: DiscoveryJob) {
    if (!selectedId) return
    setWorkingJob(job.id)
    try {
      const result = await convertDiscoveryJob(job.id, selectedId)
      window.location.assign(`/applications/${result.application_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add that application.")
      setWorkingJob(null)
    }
  }

  return (
    <main className="rp-page">
      <div className="rp-shell-wide">
        <AppTopbar />
        <section className="rp-header rp-header-grid">
          <div>
            <p className="rp-eyebrow">Relevant job discovery</p>
            <h1 className="rp-title">Find active roles worth your time.</h1>
            <p className="rp-subtitle">
              Build private searches from your target roles and resume, compare relevance signals,
              and move a verified posting into your application workflow in one step.
            </p>
          </div>
          <div className="rp-panel-strong rp-section">
            <p className="rp-eyebrow text-zinc-300">Discovery workspace</p>
            <div className="mt-5 grid grid-cols-2 gap-4">
              <Snapshot label="Active catalog" value={catalog?.active_job_count ?? 0} />
              <Snapshot label="Visible roles" value={jobs.length} />
            </div>
            <p className="mt-5 border-t border-white/10 pt-4 text-sm leading-6 text-zinc-300">
              {catalog?.last_verified_at
                ? `Catalog verified ${relativeTime(catalog.last_verified_at)} across ${catalog.active_source_count} active source postings.`
                : "The catalog has not been ingested yet. An operator must enable at least one public ATS board and run the sync."}
            </p>
          </div>
        </section>

        {error && <div className="rp-error mb-4" role="alert">{error}</div>}

        <div className="grid gap-4 lg:grid-cols-[330px_minmax(0,1fr)]">
          <aside className="space-y-4">
            <section className="rp-panel rp-section">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="rp-eyebrow">Saved searches</p>
                  <h2 className="rp-section-title mt-2">Your role profiles</h2>
                </div>
                <button type="button" onClick={beginNew} className="rp-button-primary">New</button>
              </div>
              <div className="mt-5 grid gap-2">
                {loading ? <div className="rp-skeleton h-20" /> : searches.length === 0 ? (
                  <p className="rp-section-copy">Create a search to see matching jobs.</p>
                ) : searches.map((search) => (
                  <button
                    key={search.id}
                    type="button"
                    onClick={() => selectSearch(search)}
                    className={`rp-search-option ${search.id === selectedId ? "rp-search-option-active" : ""}`}
                  >
                    <span className="font-bold">{search.name}</span>
                    <span className="mt-1 block text-xs text-[var(--muted)]">
                      {search.target_titles.slice(0, 2).join(" · ")} · {labelRecency(search.recency)}
                    </span>
                  </button>
                ))}
              </div>
              {selected && !editing && (
                <div className="mt-4 flex gap-2 border-t border-[var(--border)] pt-4">
                  <button type="button" className="rp-button-secondary flex-1" onClick={beginEdit}>Edit</button>
                  <button type="button" className="rp-button-danger" onClick={removeSearch}>Delete</button>
                </div>
              )}
            </section>
          </aside>

          <section className="space-y-4">
            {editing ? (
              <SearchEditor form={form} setForm={setForm} resumes={resumes} saving={saving}
                onSubmit={saveSearch} onCancel={() => setEditing(false)} isEditing={Boolean(selectedId)} />
            ) : selected ? (
              <>
                <section className="rp-panel rp-section">
                  <div className="flex flex-wrap items-end justify-between gap-4">
                    <div>
                      <p className="rp-eyebrow">{selected.name}</p>
                      <h2 className="rp-section-title mt-2">Matching roles</h2>
                      <p className="rp-section-copy">{selected.target_titles.join(" · ")}</p>
                    </div>
                    <div className="flex flex-wrap gap-3">
                      <SelectControl label="Recency" value={recency} options={RECENCY_OPTIONS}
                        onChange={(value) => { setRecency(value as JobRecency); void loadFeed(selected.id, value as JobRecency, sort) }} />
                      <SelectControl label="Sort" value={sort} options={SORT_OPTIONS}
                        onChange={(value) => { setSort(value as JobSort); void loadFeed(selected.id, recency, value as JobSort) }} />
                    </div>
                  </div>
                </section>
                {loadingFeed ? <div className="rp-panel rp-section"><div className="rp-skeleton h-40" /></div>
                  : jobs.length === 0 ? <EmptyFeed recency={recency} />
                  : jobs.map((job) => <JobCard key={job.id} job={job} busy={workingJob === job.id}
                      onAction={action} onHide={hideCompany} onConvert={convert} />)}
              </>
            ) : (
              <section className="rp-panel rp-section">
                <div className="rp-empty">
                  <p className="rp-eyebrow">Start here</p>
                  <h2 className="rp-section-title mt-2">Define your first search</h2>
                  <p className="rp-section-copy">Choose target titles, locations, workplace preferences, and the resume used for matching.</p>
                  <button type="button" onClick={beginNew} className="rp-button-primary mt-5">Create Saved Search</button>
                </div>
              </section>
            )}
          </section>
        </div>
      </div>
    </main>
  )
}

function SearchEditor({ form, setForm, resumes, saving, onSubmit, onCancel, isEditing }: {
  form: SearchForm
  setForm: React.Dispatch<React.SetStateAction<SearchForm>>
  resumes: ResumeListItem[]
  saving: boolean
  onSubmit: (event: React.FormEvent) => void
  onCancel: () => void
  isEditing: boolean
}) {
  const set = <K extends keyof SearchForm>(key: K, value: SearchForm[K]) =>
    setForm((current) => ({ ...current, [key]: value }))
  return (
    <form onSubmit={onSubmit} className="rp-panel rp-section">
      <p className="rp-eyebrow">{isEditing ? "Edit search" : "New search"}</p>
      <h2 className="rp-section-title mt-2">Search preferences</h2>
      <p className="rp-section-copy">Separate multiple values with commas. Target titles are required.</p>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <Field label="Search name" required><input className="rp-input" required value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Software engineering internships" /></Field>
        <Field label="Resume for match signal"><select className="rp-input" value={form.resume_id ?? ""} onChange={(e) => set("resume_id", e.target.value ? Number(e.target.value) : null)}><option value="">Default resume</option>{resumes.map((resume) => <option key={resume.id} value={resume.id}>{resume.label}{resume.is_default ? " (default)" : ""}</option>)}</select></Field>
        <Field label="Target titles" required><input className="rp-input" required value={form.target_titles} onChange={(e) => set("target_titles", e.target.value)} placeholder="Software Engineer Intern, Backend Intern" /></Field>
        <Field label="Adjacent titles"><input className="rp-input" value={form.adjacent_titles} onChange={(e) => set("adjacent_titles", e.target.value)} placeholder="Platform Intern, Developer Intern" /></Field>
        <Field label="Locations"><input className="rp-input" value={form.locations} onChange={(e) => set("locations", e.target.value)} placeholder="Chicago, New York, United States" /></Field>
        <Field label="Workplace types"><input className="rp-input" value={form.workplace_types} onChange={(e) => set("workplace_types", e.target.value)} placeholder="Remote, Hybrid, On-site" /></Field>
        <Field label="Seniority levels"><input className="rp-input" value={form.seniority_levels} onChange={(e) => set("seniority_levels", e.target.value)} placeholder="Intern, Entry level" /></Field>
        <Field label="Employment types"><input className="rp-input" value={form.employment_types} onChange={(e) => set("employment_types", e.target.value)} placeholder="Internship, Full-time" /></Field>
        <Field label="Required keywords"><input className="rp-input" value={form.required_keywords} onChange={(e) => set("required_keywords", e.target.value)} placeholder="Python, APIs" /></Field>
        <Field label="Excluded keywords"><input className="rp-input" value={form.excluded_keywords} onChange={(e) => set("excluded_keywords", e.target.value)} placeholder="Senior, Principal" /></Field>
        <Field label="Industries"><input className="rp-input" value={form.industries} onChange={(e) => set("industries", e.target.value)} placeholder="SaaS, Fintech" /></Field>
        <Field label="Excluded companies"><input className="rp-input" value={form.excluded_companies} onChange={(e) => set("excluded_companies", e.target.value)} placeholder="Companies you do not want to see" /></Field>
        <Field label="Minimum salary"><input className="rp-input" type="number" min="0" value={form.salary_min ?? ""} onChange={(e) => set("salary_min", e.target.value ? Number(e.target.value) : null)} /></Field>
        <Field label="Maximum salary"><input className="rp-input" type="number" min="0" value={form.salary_max ?? ""} onChange={(e) => set("salary_max", e.target.value ? Number(e.target.value) : null)} /></Field>
        <Field label="Saved recency"><select className="rp-input" value={form.recency} onChange={(e) => set("recency", e.target.value as JobRecency)}>{RECENCY_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
        <Field label="Digest frequency"><select className="rp-input" value={form.notification_frequency} onChange={(e) => set("notification_frequency", e.target.value as SearchForm["notification_frequency"])}><option value="off">Off</option><option value="daily">Daily (when enabled)</option><option value="weekly">Weekly (when enabled)</option></select></Field>
      </div>
      <div className="mt-6 flex justify-end gap-3 border-t border-[var(--border)] pt-5">
        <button type="button" className="rp-button-secondary" onClick={onCancel}>Cancel</button>
        <button type="submit" className="rp-button-primary" disabled={saving}>{saving ? "Saving…" : "Save Search"}</button>
      </div>
    </form>
  )
}

function JobCard({ job, busy, onAction, onHide, onConvert }: {
  job: DiscoveryJob
  busy: boolean
  onAction: (job: DiscoveryJob, state: Exclude<DiscoveryActionState, "converted">) => void
  onHide: (job: DiscoveryJob) => void
  onConvert: (job: DiscoveryJob) => void
}) {
  const source = job.sources[0]
  return (
    <article className="rp-panel rp-section">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap gap-2">
            <span className="rp-badge">{job.freshness_label}</span>
            {job.workplace_type && <span className="rp-badge">{job.workplace_type}</span>}
            {job.employment_type && <span className="rp-badge">{job.employment_type}</span>}
            {job.action_state && <span className="rp-badge capitalize">{job.action_state}</span>}
          </div>
          <h3 className="mt-4 text-2xl font-bold tracking-[-0.035em]">{job.title}</h3>
          <p className="mt-1 text-sm font-semibold">{job.company_name}<span className="font-normal text-[var(--muted)]"> · {job.location || "Location unavailable"}</span></p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center">
          <Score label="Preference" value={job.preference_match_score} />
          <Score label="Resume" value={job.resume_match_score} />
        </div>
      </div>
      {job.match_reasons.length > 0 && <ul className="mt-5 flex flex-wrap gap-2">{job.match_reasons.map((reason) => <li key={reason} className="rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--accent-strong)]">{reason}</li>)}</ul>}
      <p className="mt-5 line-clamp-3 text-sm leading-6 text-[var(--muted)]">{job.description}</p>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border)] pt-5">
        <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--muted)]">
          {source && <a href={source.canonical_url} target="_blank" rel="noreferrer" className="font-bold text-[var(--accent-strong)] hover:underline">View on {source.source_name}</a>}
          {job.sources.length > 1 && <span>{job.sources.length} verified sources</span>}
          <span>{job.source_posted_at ? `Posted ${formatDate(job.source_posted_at)}` : "Source date unavailable"}</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="rp-button-secondary" disabled={busy} onClick={() => onAction(job, "saved")}>{job.action_state === "saved" ? "Unsave" : "Save"}</button>
          <button type="button" className="rp-button-secondary" disabled={busy} onClick={() => onAction(job, "dismissed")}>Dismiss</button>
          <button type="button" className="rp-button-secondary" disabled={busy} onClick={() => onAction(job, "duplicate")}>Duplicate</button>
          <button type="button" className="rp-button-secondary" disabled={busy} onClick={() => onHide(job)}>Hide company</button>
          <button type="button" className="rp-button-primary" disabled={busy || job.action_state === "converted"} onClick={() => onConvert(job)}>{job.action_state === "converted" ? "In Applications" : "Add to Applications"}</button>
        </div>
      </div>
    </article>
  )
}

function EmptyFeed({ recency }: { recency: JobRecency }) {
  return <section className="rp-panel rp-section"><div className="rp-empty"><p className="rp-eyebrow">No matches in this view</p><h2 className="rp-section-title mt-2">Try a wider recency window or broader preferences.</h2><p className="rp-section-copy">If every view is empty, the operator still needs to enable ATS board identifiers and run the ingestion sync. You can continue with manual entry at any time.</p><Link href="/applications/new" className="rp-button-secondary mt-5">Add a job manually</Link><span className="ml-3 text-xs text-[var(--muted)]">Current window: {labelRecency(recency)}</span></div></section>
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return <label className="block"><span className="rp-field-label">{label}{required ? " *" : ""}</span>{children}</label>
}

function SelectControl({ label, value, options, onChange }: { label: string; value: string; options: Array<[string, string]>; onChange: (value: string) => void }) {
  return <label><span className="rp-field-label">{label}</span><select className="rp-input min-w-40" value={value} onChange={(event) => onChange(event.target.value)}>{options.map(([option, text]) => <option key={option} value={option}>{text}</option>)}</select></label>
}

function Score({ label, value }: { label: string; value: number | null }) {
  return <div className="rounded-lg bg-[var(--surface-muted)] px-3 py-2"><p className="font-mono text-lg font-bold">{value === null ? "—" : `${Math.round(value * 100)}%`}</p><p className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">{label}</p></div>
}

function Snapshot({ label, value }: { label: string; value: number }) {
  return <div><p className="font-mono text-3xl font-bold">{value}</p><p className="mt-1 text-xs text-zinc-300">{label}</p></div>
}

function labelRecency(value: JobRecency) {
  return RECENCY_OPTIONS.find(([option]) => option === value)?.[1] ?? value
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
}

function relativeTime(value: string) {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000))
  if (seconds < 60) return "just now"
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}
