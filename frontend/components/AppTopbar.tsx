import Link from "next/link"

import AccountMenu from "@/components/AccountMenu"

export default function AppTopbar() {
  return (
    <nav className="rp-topbar" aria-label="Primary navigation">
      <Link href="/applications" className="rp-brand">
        <span className="rp-brand-mark">RP</span>
        <span>RolePilot</span>
      </Link>
      <div className="rp-nav">
        <Link href="/applications" className="rp-nav-link">Dashboard</Link>
        <Link href="/discover" className="rp-nav-link">Discover Jobs</Link>
        <Link href="/resume" className="rp-nav-link">Resumes</Link>
        <Link href="/evidence" className="rp-nav-link">Evidence</Link>
        <Link href="/applications/new" className="rp-button-primary">Add Application</Link>
        <AccountMenu />
      </div>
    </nav>
  )
}
