export function getStatusClasses(status: string) {
  switch (status.toLowerCase()) {
    case "saved":
      return "border-zinc-700 bg-zinc-900 text-zinc-200";
    case "applied":
      return "border-blue-800 bg-blue-950/60 text-blue-300";
    case "interview":
      return "border-amber-800 bg-amber-950/60 text-amber-300";
    case "offer":
      return "border-emerald-800 bg-emerald-950/60 text-emerald-300";
    case "rejected":
      return "border-red-800 bg-red-950/60 text-red-300";
    default:
      return "border-zinc-700 bg-zinc-900 text-zinc-200";
  }
}