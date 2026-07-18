import Link from "next/link";
import AccountMenu from "@/components/AccountMenu";
import { getApplication } from "@/lib/server-api";
import EditApplicationForm from "./EditApplicationForm";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function EditApplicationPage({ params }: PageProps) {
  const { id } = await params;
  const application = await getApplication(Number(id));

  return (
    <main className="rp-page">
      <div className="rp-shell">
        <nav className="rp-topbar" aria-label="Primary navigation">
          <Link href="/applications" className="rp-brand">
            <span className="rp-brand-mark">RP</span>
            <span>RolePilot</span>
          </Link>
          <div className="rp-nav">
            <Link href={`/applications/${application.id}`} className="rp-nav-link">
              Back to Application
            </Link>
            <Link href="/applications" className="rp-nav-link">
              Dashboard
            </Link>
            <AccountMenu />
          </div>
        </nav>

        <section className="rp-header">
          <div>
            <p className="rp-eyebrow">Application editor</p>
            <h1 className="rp-title">{application.company}</h1>
            <p className="rp-subtitle">
              Update the role, status, posting context, and AI summary without changing
              the rest of your resume workflow.
            </p>
          </div>
        </section>

        <div className="rp-panel rp-section">
          <EditApplicationForm application={application} />
        </div>
      </div>
    </main>
  );
}
