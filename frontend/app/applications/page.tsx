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
  const activeCount = appliedCount + interviewCount;
  const latestApplication = applications[0];

  return (
    <main className="rp-page">
      <div className="rp-shell-wide">
        <nav className="rp-topbar" aria-label="Primary navigation">
          <Link href="/applications" className="rp-brand">
            <span className="rp-brand-mark">RP</span>
            <span>RolePilot</span>
          </Link>

          <div className="rp-nav">
            <Link href="/applications" className="rp-nav-link">
              Dashboard
            </Link>
            <Link href="/resume" className="rp-nav-link">
              Resume Analyzer
            </Link>
            <Link href="/applications/new" className="rp-button-primary">
              Add Application
            </Link>
          </div>
        </nav>

        <section className="rp-header rp-header-grid">
          <div>
            <p className="rp-eyebrow">Internship command center</p>
            <h1 className="rp-title">Track every role, resume signal, and next move.</h1>
            <p className="rp-subtitle">
              A focused workspace for students managing internship applications,
              AI job parsing, resume matching, and tailored resume drafts.
            </p>
          </div>

          <div className="rp-panel-strong rp-section">
            <p className="rp-eyebrow text-zinc-300">Pipeline health</p>
            <div className="mt-6 grid grid-cols-2 gap-4">
              <div>
                <p className="font-mono text-4xl font-bold tracking-[-0.05em]">
                  {totalCount}
                </p>
                <p className="mt-1 text-sm text-zinc-300">tracked roles</p>
              </div>
              <div>
                <p className="font-mono text-4xl font-bold tracking-[-0.05em]">
                  {activeCount}
                </p>
                <p className="mt-1 text-sm text-zinc-300">active pursuits</p>
              </div>
            </div>

            <div className="mt-7 border-t border-white/10 pt-5">
              <p className="text-sm text-zinc-300">Latest activity</p>
              <p className="mt-2 text-base font-semibold">
                {latestApplication
                  ? `${latestApplication.company} - ${latestApplication.role_title}`
                  : "No applications yet"}
              </p>
            </div>
          </div>
        </section>

        <section className="rp-panel mb-4 overflow-hidden">
          <div className="rp-metric-grid">
            <Metric label="Total" value={totalCount} />
            <Metric label="Saved" value={savedCount} />
            <Metric label="Applied" value={appliedCount} />
            <Metric label="Interview" value={interviewCount} />
            <Metric label="Offer" value={offerCount} />
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_330px]">
          <div className="rp-panel overflow-hidden">
            <div className="flex flex-col gap-3 border-b border-[var(--border)] p-5 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="rp-eyebrow">Application tracker</p>
                <h2 className="rp-section-title mt-2">Open roles</h2>
              </div>
              <p className="text-sm text-[var(--muted)]">
                Click a row to inspect fit, evidence, and tailored drafts.
              </p>
            </div>

            {applications.length === 0 ? (
              <div className="p-5">
                <div className="rp-empty">
                  <p className="rp-section-title">No applications yet</p>
                  <p className="rp-section-copy">
                    Add your first internship posting to start parsing job requirements,
                    matching your resume, and generating tailored bullets.
                  </p>
                  <Link href="/applications/new" className="rp-button-primary mt-5 w-fit">
                    Add First Application
                  </Link>
                </div>
              </div>
            ) : (
              <>
                <div className="hidden lg:block">
                  <div className="grid grid-cols-[1.2fr_1fr_150px_150px_120px] border-b border-[var(--border)] bg-[var(--surface-muted)] px-5 py-3 text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted)]">
                    <span>Company</span>
                    <span>Role</span>
                    <span>Status</span>
                    <span>Location</span>
                    <span>Created</span>
                  </div>
                  <div className="divide-y divide-[var(--border)]">
                    {applications.map((app) => (
                      <Link
                        key={app.id}
                        href={`/applications/${app.id}`}
                        className="grid grid-cols-[1.2fr_1fr_150px_150px_120px] items-center px-5 py-4 text-sm transition hover:bg-[var(--surface-muted)]"
                      >
                        <span className="font-semibold text-[var(--foreground)]">
                          {app.company}
                        </span>
                        <span className="truncate text-[var(--muted)]">{app.role_title}</span>
                        <span
                          className={`rp-badge w-fit capitalize ${getStatusClasses(app.status)}`}
                        >
                          {app.status}
                        </span>
                        <span className="truncate text-[var(--muted)]">
                          {app.location || "Remote / TBD"}
                        </span>
                        <span className="font-mono text-xs text-[var(--muted)]">
                          {formatDate(app.created_at)}
                        </span>
                      </Link>
                    ))}
                  </div>
                </div>

                <div className="grid gap-3 p-4 lg:hidden">
                  {applications.map((app) => (
                    <Link
                      key={app.id}
                      href={`/applications/${app.id}`}
                      className="rounded-lg border border-[var(--border)] bg-white p-4 transition hover:border-[var(--border-strong)] hover:bg-[var(--surface-muted)]"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="text-lg font-bold tracking-[-0.03em]">
                            {app.company}
                          </h3>
                          <p className="mt-1 text-sm text-[var(--muted)]">
                            {app.role_title}
                          </p>
                        </div>
                        <span className={`rp-badge capitalize ${getStatusClasses(app.status)}`}>
                          {app.status}
                        </span>
                      </div>
                      <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-[var(--muted)]">
                        <p>
                          <span className="font-bold text-[var(--foreground)]">Location</span>
                          <br />
                          {app.location || "Remote / TBD"}
                        </p>
                        <p>
                          <span className="font-bold text-[var(--foreground)]">Created</span>
                          <br />
                          {formatDate(app.created_at)}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              </>
            )}
          </div>

          <aside className="rp-panel rp-section h-fit">
            <p className="rp-eyebrow">Workflow map</p>
            <h2 className="rp-section-title mt-2">From posting to tailored resume</h2>
            <div className="mt-5 space-y-4">
              {[
                ["01", "Save role", "Track company, status, links, and description."],
                ["02", "Parse signal", "Extract skills, keywords, summary, and next steps."],
                ["03", "Match resume", "Compare saved resume evidence against the job."],
                ["04", "Tailor draft", "Generate bullets and export a final resume."],
              ].map(([step, title, copy]) => (
                <div key={step} className="grid grid-cols-[44px_1fr] gap-3">
                  <span className="font-mono text-xs font-bold text-[var(--accent)]">
                    {step}
                  </span>
                  <div>
                    <p className="text-sm font-bold">{title}</p>
                    <p className="mt-1 text-sm leading-6 text-[var(--muted)]">{copy}</p>
                  </div>
                </div>
              ))}
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rp-metric">
      <p className="rp-metric-label">{label}</p>
      <p className="rp-metric-value">{value}</p>
    </div>
  );
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}
