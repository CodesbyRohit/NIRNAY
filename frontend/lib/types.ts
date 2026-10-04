export type AnalysisRequest = {
  content: string;
  consent: boolean;
};

export type ClaimKind = "factual" | "financial" | "promotional";

export type ExtractedClaim = {
  id: string;
  text: string;
  kind: ClaimKind;
};

export type AnalysisResponse = {
  analysis_id: string;
  status: "completed";
  claims: ExtractedClaim[];
};

export type ClaimEvidence = {
  claim_id: string;
  sources: EvidenceSource[];
};

export type EvidenceSource = {
  evidence_id: string;
  title: string;
  url: string;
  domain: string;
  source_tier: "tier_1" | "tier_2" | "tier_3" | "tier_4" | "unknown";
  evidence: {
    status:
      | "relevant_evidence_found"
      | "weak_or_partial_evidence"
      | "source_inaccessible"
      | "no_relevant_evidence_found";
    excerpt: string | null;
    excerpt_source:
      | "search_provider_snippet"
      | "demo_fixture"
      | "source_page_excerpt"
      | null;
  };
  published_date: string | null;
  origin: "live_search" | "demo_fixture";
};

export type EvidenceResponse = {
  results: ClaimEvidence[];
};

export type AssessmentState =
  | "Supported"
  | "Contradicted"
  | "Unverified"
  | "Needs more evidence";

export type ManipulationSignalType =
  | "GUARANTEED_RETURN"
  | "URGENCY"
  | "SCARCITY_FOMO"
  | "AUTHORITY_CLAIM"
  | "INSIDER_SECRET_LANGUAGE"
  | "EXAGGERATED_CERTAINTY"
  | "TESTIMONIAL_SOCIAL_PROOF_PRESSURE"
  | "UNSUPPORTED_STATISTICAL_CLAIM";

export type ManipulationSignal = {
  signal_id: string;
  signal_type: ManipulationSignalType;
  matched_text: string;
  explanation: string;
};

export type ClaimAssessment = {
  assessment: AssessmentState;
  rationale: string;
  evidence_ids: string[];
  uncertainty: string;
};

export type AssessedClaimResult = {
  claim: ExtractedClaim;
  assessment: ClaimAssessment;
  evidence: EvidenceSource[];
  manipulation_signals: ManipulationSignal[];
};

export type CompleteAnalysisResponse = {
  analysis_id: string;
  status: "completed";
  manipulation_signals: ManipulationSignal[];
  results: AssessedClaimResult[];
};

export type ScreenshotAnalysisResponse = {
  input_type: "screenshot";
  ocr_text: string;
  content_type: "image/jpeg" | "image/png" | "image/webp";
  size_bytes: number;
  analysis: CompleteAnalysisResponse;
};

export type HealthResponse = {
  status: "ok";
};
