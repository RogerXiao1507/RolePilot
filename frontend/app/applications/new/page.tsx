import Link from "next/link";
import AccountMenu from "@/components/AccountMenu";
import ApplicationForm from "./ApplicationForm";

export default function NewApplicationPage() {
  return (
    <main className="rp-page">
      <div className="rp-shell">
        <nav className="rp-topbar" aria-label="Primary navigation">
          <Link href="/applications" className="rp-brand">
            <span className="rp-brand-mark">RP</span>
            <span>RolePilot</span>
          </Link>
          <div className="rp-nav">
            <Link href="/applications" className="rp-nav-link">
              Back to Dashboard
            </Link>
            <Link href="/resume" className="rp-nav-link">
              Resume Analyzer
            </Link>
            <AccountMenu />
          </div>
        </nav>

        <section className="rp-header">
          <div>
            <p className="rp-eyebrow">New application intake</p>
            <h1 className="rp-title">Turn a posting into an application record.</h1>
            <p className="rp-subtitle">
              Paste a URL or job description, let RolePilot extract the signal, then
              save the role into your internship pipeline.
            </p>
          </div>
        </section>

        <ApplicationForm />
      </div>
    </main>
  );
}
