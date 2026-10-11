import { Badge } from "@/components/ui/Badge";
import { ASSESSMENT_COPY } from "@/lib/labels";
import type { AssessmentState } from "@/lib/types";

export function AssessmentBadge({
  state,
  size = "md",
}: {
  state: AssessmentState;
  size?: "md" | "lg";
}) {
  const copy = ASSESSMENT_COPY[state];
  return (
    <Badge icon={copy.icon} size={size} tone={copy.tone}>
      {copy.label}
    </Badge>
  );
}
