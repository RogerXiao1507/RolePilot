import Link from "next/link";
import AccountMenu from "@/components/AccountMenu";
import { getApplication, getResume, getResumes } from "@/lib/server-api";
import DeleteButton from "./DeleteButton";
import ResumeJobMatchCard from "./ResumeJobMatchCard";
import ExpandableTextCard from "./ExpandableTextCard";
import { getStatusClasses } from "@/lib/statusStyles";
import TailoredResumeCard from "./TailoredResumeCard";
import FullTailoredResumeDraftCard from "./FullTailoredResumeDraftCard";
import ApplicationResumeSelector from "./ApplicationResumeSelector";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function ApplicationDetailPage({ params }: PageProps) {
  const { id } = await params;
  const [application, resumes] = await Promise.all([
    getApplication(Number(id)),
    getResumes(),
  ]);
  const selectedResumeItem =
    resumes.find((resume) => resume.id === application.selected_resume_id) ??
    resumes.find((resume) => resume.is_default) ??
    null;
  const selectedResume = selectedResumeItem
    ? await getResume(selectedResumeItem.id)
    : null;

  const requiredSkills = application.required_skills ?? [];
  const preferredSkills = application.preferred_skills ?? [];
  const keywords = application.keywords ?? [];
  const nextSteps = application.next_steps ?? [];

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
            <Link href="/discover" className="rp-nav-link">
              Discover Jobs
            </Link>
            <Link href="/resume" className="rp-nav-link">
              Resumes
            </Link>
            <Link href="/evidence" className="rp-nav-link">
              Evidence
            </Link>
            <Link href={`/applications/${application.id}/edit`} className="rp-button-secondary">
              Edit Application
            </Link>
            <AccountMenu />
          </div>
        </nav>

        <section className="rp-header rp-header-grid">
          <div>
            <p className="rp-eyebrow">Application dossier</p>
            <h1 className="rp-title">{application.company}</h1>
            <p className="rp-subtitle">
              {application.role_title}
              {application.location ? ` in ${application.location}` : ""}
            </p>

            <div className="mt-6 flex flex-wrap gap-2">
              <span className={`rp-badge capitalize ${getStatusClasses(application.status)}`}>
                {application.status}
              </span>
              <span className="rp-badge">
                Created {new Date(application.created_at).toLocaleDateString()}
              </span>
              {application.job_url && (
                <a
                  href={application.job_url}
                  target="_blank"
                  rel="noreferrer"
                  className="rp-badge border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100"
                >
                  View Posting
                </a>
              )}
            </div>
          </div>

          <aside className="rp-panel-strong rp-section">
            <p className="rp-eyebrow text-zinc-300">Signal snapshot</p>
            <div className="mt-5 grid grid-cols-3 gap-3">
              <Snapshot label="Required" value={requiredSkills.length} />
              <Snapshot label="Preferred" value={preferredSkills.length} />
              <Snapshot label="Keywords" value={keywords.length} />
            </div>
            <div className="mt-6 border-t border-white/10 pt-5">
              <p className="text-sm text-zinc-300">Next action</p>
              <p className="mt-2 text-base font-semibold">
                {nextSteps[0] || "Run resume match and generate tailored bullets."}
              </p>
            </div>
          </aside>
        </section>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="space-y-4">
            <section className="rp-panel rp-section">
              <p className="rp-eyebrow">Posting context</p>
              <div className="mt-5 space-y-6">
                <ExpandableTextCard
                  title="Job Description"
                  text={application.job_description || "No job description provided."}
                  collapsedHeight={300}
                />

                <ExpandableTextCard
                  title="AI Summary"
                  text={application.ai_summary || "No AI summary provided."}
                  collapsedHeight={220}
                />
              </div>
            </section>

            <section className="rp-panel rp-section">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="rp-eyebrow">Role signal</p>
                  <h2 className="rp-section-title mt-2">Skills, keywords, and next steps</h2>
                </div>
                <p className="text-sm text-[var(--muted)]">
                  Extracted from the saved posting.
                </p>
              </div>

              <div className="mt-5 grid gap-4 lg:grid-cols-3">
                <TagPanel title="Required Skills" items={requiredSkills} tone="info" />
                <TagPanel title="Preferred Skills" items={preferredSkills} tone="accent" />
                <TagPanel title="Keywords" items={keywords} tone="neutral" />
              </div>

              <div className="mt-5 rounded-lg border border-[var(--border)] bg-white p-5">
                <h3 className="text-sm font-bold">Next Steps</h3>
                {nextSteps.length > 0 ? (
                  <ol className="mt-3 space-y-3">
                    {nextSteps.map((step, index) => (
                      <li key={step} className="grid grid-cols-[36px_1fr] gap-3 text-sm">
                        <span className="font-mono text-xs font-bold text-[var(--accent)]">
                          {String(index + 1).padStart(2, "0")}
                        </span>
                        <span className="leading-6 text-[var(--foreground)]">{step}</span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mt-2 text-sm text-[var(--muted)]">No next steps saved.</p>
                )}
              </div>
            </section>

            <TailoredResumeCard applicationId={application.id} resume={selectedResume} />
            <FullTailoredResumeDraftCard applicationId={application.id} resume={selectedResume} />
          </div>

          <aside className="space-y-4 lg:sticky lg:top-5 lg:self-start">
            <ApplicationResumeSelector
              applicationId={application.id}
              resumes={resumes}
              selectedResumeId={selectedResume?.id ?? null}
            />
            <section className="rp-panel rp-section">
              <p className="rp-eyebrow">Controls</p>
              <div className="mt-4 grid gap-3">
                <Link
                  href={`/applications/${application.id}/edit`}
                  className="rp-button-secondary w-full"
                >
                  Edit Application
                </Link>
                <DeleteButton id={application.id} />
              </div>
            </section>

            <ResumeJobMatchCard applicationId={application.id} resume={selectedResume} />
          </aside>
        </div>
      </div>
    </main>
  );
}

function Snapshot({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="font-mono text-3xl font-bold tracking-[-0.05em]">{value}</p>
      <p className="mt-1 text-xs text-zinc-300">{label}</p>
    </div>
  );
}

function TagPanel({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "accent" | "info" | "neutral";
}) {
  const toneClasses = {
    accent: "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]",
    info: "border-blue-200 bg-blue-50 text-blue-700",
    neutral: "border-zinc-300 bg-zinc-100 text-zinc-700",
  };

  return (
    <div className="rounded-lg border border-[var(--border)] bg-white p-4">
      <h3 className="text-sm font-bold">{title}</h3>
      <div className="mt-3 flex flex-wrap gap-2">
        {items.length > 0 ? (
          items.map((item) => (
            <span key={item} className={`rp-badge ${toneClasses[tone]}`}>
              {item}
            </span>
          ))
        ) : (
          <p className="text-sm text-[var(--muted)]">None saved.</p>
        )}
      </div>
    </div>
  );
}
