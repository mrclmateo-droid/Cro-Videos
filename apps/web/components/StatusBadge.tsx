"use client";
import { Loader2 } from "lucide-react";
import { Badge } from "./ui";
import { PROJECT_STATUS } from "@/lib/status";

export function StatusBadge({ status }: { status: string }) {
  const s = PROJECT_STATUS[status] ?? { label: status, tone: "gray" as const };
  return (
    <Badge tone={s.tone}>
      {s.busy && <Loader2 className="h-3 w-3 animate-spin" />}
      {s.label}
    </Badge>
  );
}
