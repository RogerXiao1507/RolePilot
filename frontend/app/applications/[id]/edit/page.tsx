import Link from "next/link";
import { getApplication } from "@/lib/api";
import EditApplicationForm from "./EditApplicationForm";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function EditApplicationPage({ params }: PageProps) {
  const { id } = await params;
  const application = await getApplication(Number(id));

  return (
    <main className="min-h-screen bg-[#0a0a0b] px-6 py-10 text-zinc-100">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8">
          <Link
            href={`/applications/${application.id}`}
            className="text-sm text-zinc-400 underline underline-offset-4 transition hover:text-zinc-200"
          >
            Back to application
          </Link>
        </div>

        <div className="mb-8">
          <h1 className="text-5xl font-bold tracking-tight text-white">RolePilot</h1>
          <p className="mt-2 text-sm text-zinc-400">
            Edit application details and update progress.
          </p>
        </div>

        <div className="rounded-3xl border border-zinc-800 bg-zinc-950/80 p-8 shadow-sm">
          <EditApplicationForm application={application} />
        </div>
      </div>
    </main>
  );
}