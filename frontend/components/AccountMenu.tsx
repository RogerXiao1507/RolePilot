"use client";

import { useUser } from "@auth0/nextjs-auth0/client";

export default function AccountMenu() {
  const { user, isLoading } = useUser();

  if (isLoading || !user) return null;

  const label = user.name || user.email || "Account";
  const initial = label.slice(0, 1).toUpperCase();

  return (
    <details className="rp-account-menu">
      <summary className="rp-account-trigger">
        <span className="rp-account-avatar" aria-hidden="true">
          {initial}
        </span>
        <span className="max-w-32 truncate">{label}</span>
      </summary>
      <div className="rp-account-popover">
        <p className="text-xs font-bold uppercase tracking-wider text-[var(--muted)]">
          Signed in
        </p>
        {user.email && <p className="mt-2 truncate text-sm">{user.email}</p>}
        <a href="/auth/logout" className="rp-button-secondary mt-4 w-full">
          Sign out
        </a>
      </div>
    </details>
  );
}
