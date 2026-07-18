import { redirect } from "next/navigation";

import { auth0 } from "@/lib/auth0";

export default async function LoginPage() {
  const session = await auth0.getSession();
  if (session) {
    redirect("/applications");
  }

  return (
    <main className="rp-page grid min-h-dvh place-items-center p-4">
      <section className="rp-panel w-full max-w-lg p-8 sm:p-10">
        <div className="rp-brand w-fit">
          <span className="rp-brand-mark">RP</span>
          <span>RolePilot</span>
        </div>
        <p className="rp-eyebrow mt-10">Private career workspace</p>
        <h1 className="rp-title">Your resume evidence stays in your account.</h1>
        <p className="rp-subtitle">
          Sign in to analyze a resume, compare it with a role, and build a grounded
          tailored draft in a workspace isolated from every other user.
        </p>
        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          <a href="/auth/login" className="rp-button-primary">
            Sign in
          </a>
          <a href="/auth/login?screen_hint=signup" className="rp-button-secondary">
            Create account
          </a>
        </div>
      </section>
    </main>
  );
}
