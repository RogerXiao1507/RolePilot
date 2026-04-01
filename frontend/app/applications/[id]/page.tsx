import Link from "next/link";
import { getApplication } from "@/lib/api";
import DeleteButton from "./DeleteButton";
import ResumeJobMatchCard from "./ResumeJobMatchCard";
import ExpandableTextCard from "./ExpandableTextCard";
import { getStatusClasses } from "@/lib/statusStyles";
import TailoredResumeCard from "./TailoredResumeCard";
import FullTailoredResumeDraftCard from "./FullTailoredResumeDraftCard";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function ApplicationDetailPage({ params }: PageProps) {
  const { id } = await params;
  const application = await getApplication(Number(id));

  return (
    <main className="min-h-screen bg-[#0a0a0b] px-6 py-10 text-zinc-100">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8">
          <Link
            href="/applications"
            className="text-sm text-zinc-400 underline underline-offset-4 transition hover:text-zinc-200"
          >
            Back to applications
          </Link>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="rounded-3xl border border-zinc-800 bg-zinc-950/80 p-8 shadow-sm lg:col-span-2">
            <div>
              <h1 className="text-5xl font-bold tracking-tight text-white">
                {application.company}
              </h1>
              <p className="mt-3 text-2xl text-zinc-300">{application.role_title}</p>
            </div>

            <div className="mt-8 space-y-4 text-lg text-zinc-200">
              <p>
                <span className="font-medium text-zinc-500">Location:</span>{" "}
                {application.location || "N/A"}
              </p>

              <p>
                <span className="font-medium text-zinc-500">Job URL:</span>{" "}
                {application.job_url ? (
                  <a
                    href={application.job_url}
                    target="_blank"
                    rel="noreferrer"
                    className="break-all text-blue-400 underline underline-offset-2"
                  >
                    {application.job_url}
                  </a>
                ) : (
                  "N/A"
                )}
              </p>

              <p>
                <span className="font-medium text-zinc-500">Created At:</span>{" "}
                {new Date(application.created_at).toLocaleString()}
              </p>
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-5 shadow-sm">
            <div className="flex flex-col gap-3">
              <span
                className={`inline-flex w-fit rounded-full border px-4 py-2 text-sm font-medium capitalize ${getStatusClasses(
                  application.status
                )}`}
              >
                {application.status}
              </span>

              <Link
                href={`/applications/${application.id}/edit`}
                className="rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-center text-sm font-medium text-zinc-100 transition hover:border-zinc-500 hover:bg-zinc-800"
              >
                Edit
              </Link>

              <DeleteButton id={application.id} />
            </div>
          </div>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <div className="rounded-3xl border border-zinc-800 bg-zinc-950/80 p-8 shadow-sm">
              <div className="space-y-6">
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

                <div>
                  <h2 className="mb-3 text-2xl font-semibold text-white">Required Skills</h2>
                  <div className="flex flex-wrap gap-2 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5">
                    {application.required_skills && application.required_skills.length > 0 ? (
                      application.required_skills.map((skill) => (
                        <span
                          key={skill}
                          className="rounded-full border border-blue-800 bg-blue-950/60 px-3 py-1 text-sm text-blue-300"
                        >
                          {skill}
                        </span>
                      ))
                    ) : (
                      <p className="text-zinc-500">No required skills saved.</p>
                    )}
                  </div>
                </div>

                <div>
                  <h2 className="mb-3 text-2xl font-semibold text-white">Preferred Skills</h2>
                  <div className="flex flex-wrap gap-2 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5">
                    {application.preferred_skills && application.preferred_skills.length > 0 ? (
                      application.preferred_skills.map((skill) => (
                        <span
                          key={skill}
                          className="rounded-full border border-purple-800 bg-purple-950/60 px-3 py-1 text-sm text-purple-300"
                        >
                          {skill}
                        </span>
                      ))
                    ) : (
                      <p className="text-zinc-500">No preferred skills saved.</p>
                    )}
                  </div>
                </div>

                <div>
                  <h2 className="mb-3 text-2xl font-semibold text-white">Keywords</h2>
                  <div className="flex flex-wrap gap-2 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5">
                    {application.keywords && application.keywords.length > 0 ? (
                      application.keywords.map((keyword) => (
                        <span
                          key={keyword}
                          className="rounded-full border border-emerald-800 bg-emerald-950/60 px-3 py-1 text-sm text-emerald-300"
                        >
                          {keyword}
                        </span>
                      ))
                    ) : (
                      <p className="text-zinc-500">No keywords saved.</p>
                    )}
                  </div>
                </div>

                <div>
                  <h2 className="mb-3 text-2xl font-semibold text-white">Next Steps</h2>
                  <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5">
                    {application.next_steps && application.next_steps.length > 0 ? (
                      <ul className="list-disc space-y-2 pl-5 text-zinc-200">
                        {application.next_steps.map((step) => (
                          <li key={step}>{step}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-zinc-500">No next steps saved.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="lg:sticky lg:top-6">
              <ResumeJobMatchCard
                applicationId={application.id}
                company={application.company}
                roleTitle={application.role_title}
                jobSummary={application.ai_summary}
                requiredSkills={application.required_skills ?? []}
                preferredSkills={application.preferred_skills ?? []}
                keywords={application.keywords ?? []}
              />
            </div>
          </div>
        </div>
        <div className="mt-6">
          <TailoredResumeCard applicationId={application.id} />
        </div>
        <div className="mt-6">
          <FullTailoredResumeDraftCard applicationId={application.id} />
        </div>
      </div>
    </main>
  );
}