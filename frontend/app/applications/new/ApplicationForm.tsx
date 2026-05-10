"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createApplication, parseJobDescription, parseJobUrl } from "@/lib/api";
import { ParsedJob } from "@/lib/types";

export default function ApplicationForm() {
  const router = useRouter();

  const [jobText, setJobText] = useState("");
  const [jobUrlInput, setJobUrlInput] = useState("");
  const [parsedJob, setParsedJob] = useState<ParsedJob | null>(null);

  const [form, setForm] = useState({
    company: "",
    role_title: "",
    status: "saved",
    location: "",
    job_url: "",
    job_description: "",
    ai_summary: "",
    required_skills: [] as string[],
    preferred_skills: [] as string[],
    keywords: [] as string[],
    next_steps: [] as string[],
  });

  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function applyParsedJob(parsed: ParsedJob, originalJobText: string, parsedUrl?: string) {
    setParsedJob(parsed);

    setForm((prev) => ({
      ...prev,
      company: parsed.company || prev.company,
      role_title: parsed.role_title || prev.role_title,
      location: parsed.location || prev.location,
      job_url: parsedUrl || prev.job_url,
      job_description: originalJobText || prev.job_description,
      ai_summary: parsed.summary || prev.ai_summary,
      required_skills: parsed.required_skills || [],
      preferred_skills: parsed.preferred_skills || [],
      keywords: parsed.keywords || [],
      next_steps: parsed.next_steps || [],
    }));
  }

  async function handleAnalyzeJob() {
    if (!jobText.trim()) {
      setError("Paste a job description first so RolePilot can extract signal.");
      return;
    }

    setAnalyzing(true);
    setError("");

    try {
      const parsed = await parseJobDescription(jobText);
      applyParsedJob(parsed, jobText);
    } catch (err) {
      console.error(err);
      setError("Job description analysis failed. Keep your pasted text and try again.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleAnalyzeUrl() {
    if (!jobUrlInput.trim()) {
      setError("Paste a job posting URL before running URL analysis.");
      return;
    }

    setAnalyzing(true);
    setError("");

    try {
      const parsed = await parseJobUrl(jobUrlInput);
      applyParsedJob(parsed, "", jobUrlInput);
    } catch (err) {
      console.error(err);
      setError("URL analysis failed. Paste the job description manually to keep moving.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      await createApplication(form);
      router.push("/applications");
      router.refresh();
    } catch (err) {
      console.error(err);
      setError("Application could not be saved. Check the fields and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rp-panel rp-section shadow-none">
          <p className="rp-eyebrow">URL parser</p>
          <label htmlFor="job_url_input" className="rp-field-label mt-4">
            Job posting URL
          </label>
          <input
            id="job_url_input"
            value={jobUrlInput}
            onChange={(e) => setJobUrlInput(e.target.value)}
            placeholder="https://company.com/careers/internship"
            className="rp-input"
          />
          <button
            type="button"
            onClick={handleAnalyzeUrl}
            disabled={analyzing}
            className="rp-button-secondary mt-3 w-full"
          >
            {analyzing ? "Analyzing URL..." : "Analyze From URL"}
          </button>
        </div>

        <div className="rp-panel rp-section shadow-none">
          <p className="rp-eyebrow">Description parser</p>
          <label htmlFor="job_text" className="rp-field-label mt-4">
            Full job description
          </label>
          <textarea
            id="job_text"
            value={jobText}
            onChange={(e) => setJobText(e.target.value)}
            placeholder="Paste the posting here to extract skills, summary, and next steps."
            className="rp-input min-h-40 resize-y"
          />
          <button
            type="button"
            onClick={handleAnalyzeJob}
            disabled={analyzing}
            className="rp-button-secondary mt-3 w-full"
          >
            {analyzing ? "Analyzing Text..." : "Analyze Job Description"}
          </button>
        </div>
      </section>

      {parsedJob && (
        <section className="rp-panel rp-section">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="rp-eyebrow">AI job insights</p>
              <h2 className="rp-section-title mt-2">Extracted posting signal</h2>
            </div>
            <span className="rp-badge border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]">
              Ready to save
            </span>
          </div>

          <div className="mt-5 grid gap-5 lg:grid-cols-3">
            <InsightList title="Required skills" items={parsedJob.required_skills} tone="info" />
            <InsightList title="Preferred skills" items={parsedJob.preferred_skills} tone="accent" />
            <InsightList title="Next steps" items={parsedJob.next_steps} tone="warning" />
          </div>
        </section>
      )}

      <section className="rp-panel rp-section">
        <div className="mb-5">
          <p className="rp-eyebrow">Application record</p>
          <h2 className="rp-section-title mt-2">Save tracker details</h2>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Company" htmlFor="company">
            <input
              id="company"
              name="company"
              placeholder="Company"
              value={form.company}
              onChange={handleChange}
              className="rp-input"
              required
            />
          </Field>

          <Field label="Role title" htmlFor="role_title">
            <input
              id="role_title"
              name="role_title"
              placeholder="Software Engineering Intern"
              value={form.role_title}
              onChange={handleChange}
              className="rp-input"
              required
            />
          </Field>

          <Field label="Status" htmlFor="status">
            <select
              id="status"
              name="status"
              value={form.status}
              onChange={handleChange}
              className="rp-input"
            >
              <option value="saved">saved</option>
              <option value="applied">applied</option>
              <option value="interview">interview</option>
              <option value="offer">offer</option>
              <option value="rejected">rejected</option>
            </select>
          </Field>

          <Field label="Location" htmlFor="location">
            <input
              id="location"
              name="location"
              placeholder="New York, Remote, Hybrid"
              value={form.location}
              onChange={handleChange}
              className="rp-input"
            />
          </Field>

          <div className="md:col-span-2">
            <Field label="Job URL" htmlFor="job_url">
              <input
                id="job_url"
                name="job_url"
                placeholder="Saved posting URL"
                value={form.job_url}
                onChange={handleChange}
                className="rp-input"
              />
            </Field>
          </div>

          <div className="md:col-span-2">
            <Field label="Job description" htmlFor="job_description">
              <textarea
                id="job_description"
                name="job_description"
                placeholder="Job description"
                value={form.job_description}
                onChange={handleChange}
                className="rp-input min-h-44 resize-y"
              />
            </Field>
          </div>

          <div className="md:col-span-2">
            <Field label="AI summary" htmlFor="ai_summary">
              <textarea
                id="ai_summary"
                name="ai_summary"
                placeholder="AI summary"
                value={form.ai_summary}
                onChange={handleChange}
                className="rp-input min-h-32 resize-y"
              />
            </Field>
          </div>
        </div>

        {error && <div className="rp-error mt-5">{error}</div>}

        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-[var(--muted)]">
            Required fields are company and role title. Parsed skills are saved with the record.
          </p>
          <button type="submit" disabled={loading} className="rp-button-primary">
            {loading ? "Saving Application..." : "Create Application"}
          </button>
        </div>
      </section>
    </form>
  );
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="rp-field-label">
        {label}
      </label>
      {children}
    </div>
  );
}

function InsightList({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "accent" | "info" | "warning";
}) {
  const toneClasses = {
    accent: "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]",
    info: "border-blue-200 bg-blue-50 text-blue-700",
    warning: "border-amber-200 bg-amber-50 text-amber-800",
  };

  return (
    <div>
      <p className="text-sm font-bold">{title}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {items.length > 0 ? (
          items.map((item) => (
            <span key={item} className={`rp-badge ${toneClasses[tone]}`}>
              {item}
            </span>
          ))
        ) : (
          <p className="text-sm text-[var(--muted)]">None found</p>
        )}
      </div>
    </div>
  );
}
