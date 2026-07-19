"use client"

import { useEffect, useState } from "react"

import {
  convertResumeSourceToEvidence,
  getResumeSourceItems,
  updateResumeStructuredData,
} from "@/lib/api"
import type {
  ResumeSourceItem,
  ResumeStructuredData,
  ResumeStructuredEntry,
  SavedResume,
} from "@/lib/types"

type Props = {
  resume: SavedResume
  onSaved: (resume: SavedResume) => void
}

const ENTRY_SECTIONS = ["education", "experience", "projects", "other"] as const
type EntrySection = (typeof ENTRY_SECTIONS)[number]

export default function ParsedResumeEditor({ resume, onSaved }: Props) {
  const [data, setData] = useState<ResumeStructuredData>(() => structuredClone(resume.structured_data))
  const [sourceItems, setSourceItems] = useState<ResumeSourceItem[]>([])
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")

  useEffect(() => {
    setData(structuredClone(resume.structured_data))
    setMessage("")
    getResumeSourceItems(resume.id)
      .then(setSourceItems)
      .catch((err) => console.error(err))
  }, [resume.id, resume.version, resume.structured_data])

  function updateEntry(section: EntrySection, index: number, value: ResumeStructuredEntry) {
    setData({
      ...data,
      [section]: data[section].map((entry, entryIndex) => entryIndex === index ? value : entry),
    })
  }

  function addEntry(section: EntrySection) {
    setData({
      ...data,
      [section]: [
        ...data[section],
        { title: "", subtitle: null, location: null, date_range: null, bullets: [] },
      ],
    })
  }

  function removeEntry(section: EntrySection, index: number) {
    setData({ ...data, [section]: data[section].filter((_, entryIndex) => entryIndex !== index) })
  }

  async function save() {
    setSaving(true)
    setError("")
    setMessage("")
    try {
      const updated = await updateResumeStructuredData(resume.id, data)
      onSaved(updated)
      setSourceItems(await getResumeSourceItems(resume.id))
      setMessage(`Saved version ${updated.version}. Dependent drafts were marked stale.`)
    } catch (err) {
      console.error(err)
      setError("Parsed resume changes could not be saved.")
    } finally {
      setSaving(false)
    }
  }

  async function convert(item: ResumeSourceItem) {
    setError("")
    setMessage("")
    try {
      await convertResumeSourceToEvidence(item.id, {
        title: item.title || `${resume.label} ${item.section}`,
        category: item.section,
      })
      setMessage("Added to the Evidence Library and embedded for retrieval.")
    } catch (err) {
      console.error(err)
      setError("This source item could not be converted to evidence.")
    }
  }

  return (
    <section className="rp-panel rp-section">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="rp-eyebrow">Parsed source · version {resume.version}</p>
          <h2 className="rp-section-title mt-2">Structured resume sections</h2>
          <p className="rp-section-copy">
            Correct parsed fields before matching. Saving creates a new source version and marks old generated artifacts stale.
          </p>
        </div>
        <button onClick={save} disabled={saving} className="rp-button-primary">
          {saving ? "Saving…" : "Save Parsed Resume"}
        </button>
      </div>

      {message && <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</div>}
      {error && <div className="rp-error mt-4">{error}</div>}

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        {(["name", "email", "phone", "location"] as const).map((field) => (
          <label key={field} className="block">
            <span className="rp-field-label capitalize">{field}</span>
            <input
              value={data.contact[field] || ""}
              onChange={(event) => setData({ ...data, contact: { ...data.contact, [field]: event.target.value || null } })}
              className="rp-input"
            />
          </label>
        ))}
      </div>

      <label className="mt-4 block">
        <span className="rp-field-label">Skills (comma separated)</span>
        <input
          value={data.skills.join(", ")}
          onChange={(event) => setData({ ...data, skills: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })}
          className="rp-input"
        />
      </label>

      <div className="mt-6 space-y-6">
        {ENTRY_SECTIONS.map((section) => (
          <section key={section} className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold capitalize">{section}</h3>
              <button type="button" onClick={() => addEntry(section)} className="text-xs font-bold text-[var(--accent-strong)]">Add entry</button>
            </div>
            <div className="mt-3 space-y-4">
              {data[section].map((entry, index) => (
                <article key={index} className="rounded-lg border border-[var(--border)] bg-white p-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <EditorField label="Title" value={entry.title} onChange={(value) => updateEntry(section, index, { ...entry, title: value })} />
                    <EditorField label="Subtitle" value={entry.subtitle || ""} onChange={(value) => updateEntry(section, index, { ...entry, subtitle: value || null })} />
                    <EditorField label="Location" value={entry.location || ""} onChange={(value) => updateEntry(section, index, { ...entry, location: value || null })} />
                    <EditorField label="Date range" value={entry.date_range || ""} onChange={(value) => updateEntry(section, index, { ...entry, date_range: value || null })} />
                  </div>
                  <label className="mt-3 block">
                    <span className="rp-field-label">Bullets (one per line)</span>
                    <textarea
                      value={entry.bullets.join("\n")}
                      onChange={(event) => updateEntry(section, index, { ...entry, bullets: event.target.value.split("\n").map((value) => value.trim()).filter(Boolean) })}
                      rows={4}
                      className="rp-input min-h-28"
                    />
                  </label>
                  <button type="button" onClick={() => removeEntry(section, index)} className="mt-3 text-xs font-bold text-red-700">Remove entry</button>
                </article>
              ))}
              {data[section].length === 0 && <p className="text-sm text-[var(--muted)]">No {section} parsed.</p>}
            </div>
          </section>
        ))}
      </div>

      <details className="mt-6 rounded-lg border border-[var(--border)] bg-white p-4">
        <summary className="cursor-pointer text-sm font-bold">Stable source items ({sourceItems.length})</summary>
        <p className="mt-2 text-xs leading-5 text-[var(--muted)]">
          These IDs anchor future citations. Convert useful bullets into richer evidence with outcomes and verified metrics.
        </p>
        <div className="mt-4 space-y-3">
          {sourceItems.filter((item) => item.item_type === "bullet").map((item) => (
            <div key={item.id} className="rounded-lg border border-[var(--border)] p-3">
              <p className="text-xs font-bold uppercase text-[var(--muted)]">{item.section} · {item.title}</p>
              <p className="mt-2 text-sm leading-6">{item.content}</p>
              <button onClick={() => convert(item)} className="mt-3 text-xs font-bold text-[var(--accent-strong)]">Add to Evidence Library</button>
            </div>
          ))}
        </div>
      </details>
    </section>
  )
}

function EditorField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="block"><span className="rp-field-label">{label}</span><input value={value} onChange={(event) => onChange(event.target.value)} className="rp-input" /></label>
}
