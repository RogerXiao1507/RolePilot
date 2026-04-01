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
      setError("Paste a job description first.");
      return;
    }

    setAnalyzing(true);
    setError("");

    try {
      const parsed = await parseJobDescription(jobText);
      applyParsedJob(parsed, jobText);
    } catch (err) {
      console.error(err);
      setError("Failed to analyze job description.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleAnalyzeUrl() {
    if (!jobUrlInput.trim()) {
      setError("Paste a job posting URL first.");
      return;
    }

    setAnalyzing(true);
    setError("");

    try {
      const parsed = await parseJobUrl(jobUrlInput);
      applyParsedJob(parsed, "", jobUrlInput);
    } catch (err) {
      console.error(err);
      setError("Failed to analyze job URL. Try pasting the description manually.");
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
      setError("Failed to create application. Check browser console.");
    } finally {
      setLoading(false);
    }
  }

  const inputClassName =
    "w-full rounded-2xl border border-zinc-800 bg-zinc-900/70 px-4 py-3 text-zinc-100 placeholder:text-zinc-500 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20";

  const labelClassName = "mb-2 block text-sm font-medium text-zinc-300";

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="job_url_input" className={labelClassName}>
          Job Posting URL
        </label>
        <input
          id="job_url_input"
          value={jobUrlInput}
          onChange={(e) => setJobUrlInput(e.target.value)}
          placeholder="Paste a job posting link here"
          className={inputClassName}
        />
        <div className="mt-3">
          <button
            type="button"
            onClick={handleAnalyzeUrl}
            disabled={analyzing}
            className="rounded-xl border border-blue-700 bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:border-blue-600 hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {analyzing ? "Analyzing..." : "Analyze From URL"}
          </button>
        </div>
      </div>

      <div>
        <label htmlFor="job_text" className={labelClassName}>
          Paste Job Description
        </label>
        <textarea
          id="job_text"
          value={jobText}
          onChange={(e) => setJobText(e.target.value)}
          placeholder="Paste the full job description here, then click Analyze Job."
          className={`${inputClassName} min-h-48 resize-none`}
        />
        <div className="mt-3">
          <button
            type="button"
            onClick={handleAnalyzeJob}
            disabled={analyzing}
            className="rounded-xl border border-blue-700 bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:border-blue-600 hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {analyzing ? "Analyzing..." : "Analyze Job"}
          </button>
        </div>
      </div>

      {parsedJob && (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-5">
          <h3 className="text-lg font-semibold text-white">AI Job Insights</h3>

          <div className="mt-4 space-y-4 text-sm">
            <div>
              <p className="mb-2 font-medium text-zinc-300">Required Skills</p>
              <div className="flex flex-wrap gap-2">
                {parsedJob.required_skills.length > 0 ? (
                  parsedJob.required_skills.map((skill) => (
                    <span
                      key={skill}
                      className="rounded-full border border-blue-800 bg-blue-950/50 px-3 py-1 text-blue-300"
                    >
                      {skill}
                    </span>
                  ))
                ) : (
                  <p className="text-zinc-500">None found</p>
                )}
              </div>
            </div>

            <div>
              <p className="mb-2 font-medium text-zinc-300">Preferred Skills</p>
              <div className="flex flex-wrap gap-2">
                {parsedJob.preferred_skills.length > 0 ? (
                  parsedJob.preferred_skills.map((skill) => (
                    <span
                      key={skill}
                      className="rounded-full border border-purple-800 bg-purple-950/50 px-3 py-1 text-purple-300"
                    >
                      {skill}
                    </span>
                  ))
                ) : (
                  <p className="text-zinc-500">None found</p>
                )}
              </div>
            </div>

            <div>
              <p className="mb-2 font-medium text-zinc-300">Next Steps</p>
              {parsedJob.next_steps.length > 0 ? (
                <ul className="list-disc space-y-1 pl-5 text-zinc-300">
                  {parsedJob.next_steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-zinc-500">No next steps generated</p>
              )}
            </div>
          </div>
        </div>
      )}

      <div>
        <label htmlFor="company" className={labelClassName}>
          Company
        </label>
        <input
          id="company"
          name="company"
          placeholder="Company"
          value={form.company}
          onChange={handleChange}
          className={inputClassName}
          required
        />
      </div>

      <div>
        <label htmlFor="role_title" className={labelClassName}>
          Role Title
        </label>
        <input
          id="role_title"
          name="role_title"
          placeholder="Role Title"
          value={form.role_title}
          onChange={handleChange}
          className={inputClassName}
          required
        />
      </div>

      <div>
        <label htmlFor="status" className={labelClassName}>
          Status
        </label>
        <select
          id="status"
          name="status"
          value={form.status}
          onChange={handleChange}
          className={inputClassName}
        >
          <option value="saved">saved</option>
          <option value="applied">applied</option>
          <option value="interview">interview</option>
          <option value="offer">offer</option>
          <option value="rejected">rejected</option>
        </select>
      </div>

      <div>
        <label htmlFor="location" className={labelClassName}>
          Location
        </label>
        <input
          id="location"
          name="location"
          placeholder="Location"
          value={form.location}
          onChange={handleChange}
          className={inputClassName}
        />
      </div>

      <div>
        <label htmlFor="job_url" className={labelClassName}>
          Job URL
        </label>
        <input
          id="job_url"
          name="job_url"
          placeholder="Job URL"
          value={form.job_url}
          onChange={handleChange}
          className={inputClassName}
        />
      </div>

      <div>
        <label htmlFor="job_description" className={labelClassName}>
          Job Description
        </label>
        <textarea
          id="job_description"
          name="job_description"
          placeholder="Job Description"
          value={form.job_description}
          onChange={handleChange}
          className={`${inputClassName} min-h-40 resize-none`}
        />
      </div>

      <div>
        <label htmlFor="ai_summary" className={labelClassName}>
          AI Summary
        </label>
        <textarea
          id="ai_summary"
          name="ai_summary"
          placeholder="AI Summary"
          value={form.ai_summary}
          onChange={handleChange}
          className={`${inputClassName} min-h-32 resize-none`}
        />
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="rounded-xl border border-emerald-700 bg-emerald-600 px-5 py-3 text-sm font-medium text-white transition hover:border-emerald-600 hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Saving..." : "Create Application"}
      </button>
    </form>
  );
}