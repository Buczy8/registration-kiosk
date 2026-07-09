export function humanizePrintJobStatus(value) {
  if (value === "queued") return "W kolejce";
  if (value === "printing") return "W trakcie";
  if (value === "done" || value === "completed") return "Zakończone";
  if (value === "failed") return "Błąd";
  return value || "—";
}
