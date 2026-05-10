"use client";

import { useRouter } from "next/navigation";
import { deleteApplication } from "@/lib/api";

type Props = {
  id: number;
};

export default function DeleteButton({ id }: Props) {
  const router = useRouter();

  async function handleDelete() {
    const confirmed = window.confirm("Delete this application?");
    if (!confirmed) return;

    try {
      await deleteApplication(id);
      router.push("/applications");
      router.refresh();
    } catch (err) {
      console.error(err);
      alert("Failed to delete application");
    }
  }

  return (
    <button
      onClick={handleDelete}
      className="rp-button-danger w-full"
    >
      Delete
    </button>
  );
}
