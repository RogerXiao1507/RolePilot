import Link from "next/link";
import { getApplications } from "@/lib/api";
import { getStatusClasses } from "@/lib/statusStyles";

export default async function ApplicationsPage() {
  const applications = await getApplications();

  const totalCount = applications.length;
  const savedCount = applications.filter((app) => app.status === "saved").length;
  const appliedCount = applications.filter((app) => app.status === "applied").length;
  const interviewCount = applications.filter((app) => app.status === "interview").length;
  const offerCount = applications.filter((app) => app.status === "offer").length;

  return (
    <main className="min-h-screen bg-[#0a0a0b] px-6 py-10 text-zinc-100">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-5xl font-bold tracking-tight text-white">RolePilot</h1>
            <p className="mt-2 text-sm text-zinc-400">
              Track internships, interviews, and offers in one place.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <Link
              href="/resume"
              className="rounded-xl border border-zinc-800 bg-zinc-900 px-5 py-3 text-sm font-medium text-zinc-200 transition hover:border-zinc-700 hover:bg-zinc-800"
            >
              Resume Analyzer
            </Link>

            <Link
              href="/applications/new"
              className="rounded-xl border border-emerald-700 bg-emerald-600 px-5 py-3 text-sm font-medium text-white transition hover:border-emerald-600 hover:bg-emerald-500"
            >
              Add Application
            </Link>
          </div>
        </div>

        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-5 shadow-sm">
            <p className="text-sm text-zinc-400">Total</p>
            <p className="mt-3 text-3xl font-bold text-white">{totalCount}</p>
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-5 shadow-sm">
            <p className="text-sm text-zinc-400">Saved</p>
            <p className="mt-3 text-3xl font-bold text-zinc-100">{savedCount}</p>
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-5 shadow-sm">
            <p className="text-sm text-zinc-400">Applied</p>
            <p className="mt-3 text-3xl font-bold text-blue-300">{appliedCount}</p>
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-5 shadow-sm">
            <p className="text-sm text-zinc-400">Interview</p>
            <p className="mt-3 text-3xl font-bold text-amber-300">{interviewCount}</p>
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-5 shadow-sm">
            <p className="text-sm text-zinc-400">Offer</p>
            <p className="mt-3 text-3xl font-bold text-emerald-300">{offerCount}</p>
          </div>
        </div>

        {applications.length === 0 ? (
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-6">
            <p className="text-zinc-400">No applications yet.</p>
          </div>
        ) : (
          <div className="space-y-5">
            {applications.map((app) => (
              <Link key={app.id} href={`/applications/${app.id}`} className="block">
                <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-6 shadow-sm transition hover:border-zinc-700 hover:bg-zinc-900/80">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h2 className="text-3xl font-bold text-white">{app.company}</h2>
                      <p className="mt-2 text-xl text-zinc-300">{app.role_title}</p>
                    </div>

                    <span
                      className={`rounded-full border px-4 py-1.5 text-sm font-medium capitalize ${getStatusClasses(
                        app.status
                      )}`}
                    >
                      {app.status}
                    </span>
                  </div>

                  <div className="mt-6 space-y-2 text-base text-zinc-300">
                    <p>
                      <span className="text-zinc-500">Location:</span>{" "}
                      {app.location || "N/A"}
                    </p>

                    <p>
                      <span className="text-zinc-500">Job URL:</span>{" "}
                      {app.job_url ? (
                        <span className="text-blue-400 underline underline-offset-2">
                          View posting
                        </span>
                      ) : (
                        "N/A"
                      )}
                    </p>
                  </div>

                  {app.ai_summary && (
                    <div className="mt-6 rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
                      <p className="text-sm font-medium text-zinc-400">AI Summary</p>
                      <p className="mt-2 text-base leading-7 text-zinc-200">
                        {app.ai_summary}
                      </p>
                    </div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}