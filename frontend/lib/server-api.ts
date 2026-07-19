import "server-only";

import { redirect } from "next/navigation";

import { auth0 } from "@/lib/auth0";
import type { Application, ResumeListItem, SavedResume } from "@/lib/types";

const BACKEND_API_URL = (
  process.env.BACKEND_API_URL || "http://localhost:8000"
).replace(/\/$/, "");

async function authenticatedBackendFetch(path: string): Promise<Response> {
  const session = await auth0.getSession();
  if (!session) {
    redirect("/login");
  }

  const { token } = await auth0.getAccessToken();
  return fetch(`${BACKEND_API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
}

export async function getApplications(): Promise<Application[]> {
  const response = await authenticatedBackendFetch("/applications");
  if (!response.ok) {
    throw new Error("Failed to fetch applications");
  }
  return response.json();
}

export async function getApplication(id: number): Promise<Application> {
  const response = await authenticatedBackendFetch(`/applications/${id}`);
  if (!response.ok) {
    throw new Error("Failed to fetch application");
  }
  return response.json();
}

export async function getResumes(): Promise<ResumeListItem[]> {
  const response = await authenticatedBackendFetch("/resume");
  if (!response.ok) {
    throw new Error("Failed to fetch resumes");
  }
  return response.json();
}

export async function getResume(id: number): Promise<SavedResume> {
  const response = await authenticatedBackendFetch(`/resume/${id}`);
  if (!response.ok) {
    throw new Error("Failed to fetch resume");
  }
  return response.json();
}
