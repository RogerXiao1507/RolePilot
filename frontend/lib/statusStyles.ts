export function getStatusClasses(status: string) {
  switch (status.toLowerCase()) {
    case "saved":
      return "border-zinc-300 bg-zinc-100 text-zinc-700";
    case "applied":
      return "border-blue-200 bg-blue-50 text-blue-700";
    case "interview":
      return "border-amber-200 bg-amber-50 text-amber-800";
    case "offer":
      return "border-emerald-200 bg-emerald-50 text-emerald-800";
    case "rejected":
      return "border-red-200 bg-red-50 text-red-700";
    default:
      return "border-zinc-300 bg-zinc-100 text-zinc-700";
  }
}
