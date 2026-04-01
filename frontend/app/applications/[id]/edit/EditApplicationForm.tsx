"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Application } from "@/lib/types";
import { updateApplication } from "@/lib/api";

type Props = {
  application: Application;
};

export default function EditApplicationForm({ application }: Props) {
  const router = useRouter();

  const [form, setForm] = useState({
    company: application.company,
    role_title: application.role_title,
    status: application.status,
    location: application.location || "",
    job_url: application.job_url || "",
    job_description: application.job_description || "",
    ai_summary: application.ai_summary || "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      await updateApplication(application.id, form);
      router.push(`/applications/${application.id}`);
      router.refresh();
    } catch (err) {
      console.error(err);
      setError("Failed to update application");
    } finally {
      setLoading(false);
    }
  }

  const inputClassName =
    "w-full rounded-2xl border border-zinc-800 bg-zinc-900/70 px-4 py-3 text-zinc-100 placeholder:text-zinc-500 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20";

  const labelClassName = "mb-2 block text-sm font-medium text-zinc-300";

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label htmlFor="company" className={labelClassName}>
          Company
        </label>
        <input
          id="company"
          name="company"
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
        {loading ? "Saving..." : "Save Changes"}
      </button>
    </form>
  );
}