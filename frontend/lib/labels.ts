// User-facing labels and plain-English explanations for values returned by the API.
// Keeping them in one place makes it straightforward to add another locale (e.g. Hindi) later.

import type { Tone } from "@/components/ui/Badge";
import type { IconName } from "@/components/ui/Icon";
import type {
  AssessmentState,
  ClaimKind,
  EvidenceSource,
  ManipulationSignalType,
} from "@/lib/types";

type Described = { label: string; description: string };

export const ASSESSMENT_COPY: Record<
  AssessmentState,
  Described & { tone: Tone; icon: IconName }
> = {
  Supported: {
    label: "Supported",
    description:
      "The assessment found that text retrieved from at least one cited source page backs this claim. Check that the source refers to the same entity and time period.",
    tone: "supported",
    icon: "checkCircle",
  },
  Contradicted: {
    label: "Contradicted",
    description:
      "The assessment found that text retrieved from at least one cited source page conflicts with this claim.",
    tone: "contradicted",
    icon: "xCircle",
  },
  "Needs more evidence": {
    label: "Needs more evidence",
    description:
      "Some material was found, but not enough to support or contradict the claim. Search snippets and demo text are never treated as enough on their own.",
    tone: "needs",
    icon: "halfCircle",
  },
  Unverified: {
    label: "Unverified",
    description:
      "The available evidence did not establish this claim. This is not proof that the claim is false.",
    tone: "unverified",
    icon: "dashCircle",
  },
};

export const ASSESSMENT_ORDER: AssessmentState[] = [
  "Contradicted",
  "Needs more evidence",
  "Unverified",
  "Supported",
];

export const CLAIM_KIND_LABELS: Record<ClaimKind, string> = {
  factual: "Factual claim",
  financial: "Financial claim",
  promotional: "Promotional claim",
};

export const SIGNAL_LABELS: Record<ManipulationSignalType, string> = {
  GUARANTEED_RETURN: "Guaranteed-return language",
  URGENCY: "Urgency",
  SCARCITY_FOMO: "Scarcity / FOMO",
  AUTHORITY_CLAIM: "Authority claim",
  INSIDER_SECRET_LANGUAGE: "Insider / secret language",
  EXAGGERATED_CERTAINTY: "Exaggerated certainty",
  TESTIMONIAL_SOCIAL_PROOF_PRESSURE: "Testimonial / social-proof pressure",
  UNSUPPORTED_STATISTICAL_CLAIM: "Promotional numerical claim",
};

// Tiers are assigned by the backend from fixed domain lists (see backend/app/services/source_ranking.py).
export const TIER_COPY: Record<EvidenceSource["source_tier"], Described> = {
  tier_1: {
    label: "Tier 1",
    description: "Regulator, exchange, depository, or Government of India domain",
  },
  tier_2: {
    label: "Tier 2",
    description: "Financial-education body or international financial institution",
  },
  tier_3: {
    label: "Tier 3",
    description: "Established financial news publisher",
  },
  tier_4: {
    label: "Tier 4",
    description: "Other website, not on NIRNAY's reviewed domain lists",
  },
  unknown: {
    label: "Unclassified",
    description: "Source type could not be determined",
  },
};

export const EVIDENCE_STATUS_COPY: Record<
  EvidenceSource["evidence"]["status"],
  Described & { tone: Tone }
> = {
  relevant_evidence_found: {
    label: "Relevant excerpt",
    description: "The excerpt overlaps substantially with the claim's wording.",
    tone: "live",
  },
  weak_or_partial_evidence: {
    label: "Partial match",
    description: "The excerpt only partly overlaps with the claim.",
    tone: "needs",
  },
  source_inaccessible: {
    label: "Source not readable",
    description: "No usable text could be read from this source.",
    tone: "neutral",
  },
  no_relevant_evidence_found: {
    label: "No relevant excerpt",
    description: "Nothing on this source matched the claim's wording.",
    tone: "neutral",
  },
};

export function excerptSourceLabel(
  source: EvidenceSource["evidence"]["excerpt_source"],
): string {
  switch (source) {
    case "search_provider_snippet":
      return "Search-provider snippet · page not directly retrieved";
    case "source_page_excerpt":
      return "Excerpt retrieved from the source page";
    case "demo_fixture":
      return "Illustrative demo evidence · not retrieved page content";
    default:
      return "No excerpt available";
  }
}

export type Provenance = "source" | "ai" | "rule" | "demo" | "live";

export const PROVENANCE_COPY: Record<
  Provenance,
  { label: string; tone: Tone; icon: IconName }
> = {
  source: { label: "Retrieved source data", tone: "neutral", icon: "document" },
  ai: { label: "AI assessment · model-generated", tone: "ai", icon: "model" },
  rule: { label: "Rule-based pattern match", tone: "signal", icon: "rule" },
  demo: { label: "Demo fixture · not live research", tone: "demo", icon: "flask" },
  live: { label: "Live search result", tone: "live", icon: "globe" },
};
