import type {
  AssessedClaimResult,
  AssessmentState,
  CompleteAnalysisResponse,
  EvidenceSource,
} from "@/lib/types";

/**
 * Splits a claim's evidence into sources the assessment cited and sources that were only retrieved.
 * The backend's ranking order is preserved within each group.
 */
export function groupEvidence(result: AssessedClaimResult): {
  cited: EvidenceSource[];
  uncited: EvidenceSource[];
} {
  const citedIds = new Set(result.assessment.evidence_ids);
  return {
    cited: result.evidence.filter((source) => citedIds.has(source.evidence_id)),
    uncited: result.evidence.filter((source) => !citedIds.has(source.evidence_id)),
  };
}

export function hasDemoEvidence(analysis: CompleteAnalysisResponse): boolean {
  return analysis.results.some((result) =>
    result.evidence.some((source) => source.origin === "demo_fixture"),
  );
}

export function countAssessments(
  analysis: CompleteAnalysisResponse,
): Record<AssessmentState, number> {
  const counts: Record<AssessmentState, number> = {
    Supported: 0,
    Contradicted: 0,
    Unverified: 0,
    "Needs more evidence": 0,
  };
  for (const result of analysis.results) counts[result.assessment.assessment] += 1;
  return counts;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Formats an ISO-like date (YYYY-MM-DD…) as "5 Mar 2025"; other strings are shown as given. */
export function formatPublishedDate(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!match) return value;
  const [, year, month, day] = match;
  const monthIndex = Number(month) - 1;
  if (monthIndex < 0 || monthIndex > 11) return value;
  return `${Number(day)} ${MONTHS[monthIndex]} ${year}`;
}
