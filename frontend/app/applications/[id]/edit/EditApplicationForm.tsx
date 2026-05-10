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
      setError("Application updates could not be saved. Review the fields and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Company" htmlFor="company">
          <input
            id="company"
            name="company"
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
              value={form.ai_summary}
              onChange={handleChange}
              className="rp-input min-h-32 resize-y"
            />
          </Field>
        </div>
      </div>

      {error && <div className="rp-error">{error}</div>}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-[var(--muted)]">
          Changes update the saved application record used by matching and tailoring.
        </p>
        <button type="submit" disabled={loading} className="rp-button-primary">
          {loading ? "Saving Changes..." : "Save Changes"}
        </button>
      </div>
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
