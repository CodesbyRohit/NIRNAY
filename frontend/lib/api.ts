import type {
  AnalysisRequest,
  CompleteAnalysisResponse,
  EvidenceResponse,
  ExtractedClaim,
  HealthResponse,
  ManipulationSignal,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isManipulationSignal(value: unknown): value is ManipulationSignal {
  if (!isRecord(value)) return false;
  return (
    typeof value.signal_id === "string" &&
    (value.signal_type === "GUARANTEED_RETURN" ||
      value.signal_type === "URGENCY" ||
      value.signal_type === "SCARCITY_FOMO" ||
      value.signal_type === "AUTHORITY_CLAIM" ||
      value.signal_type === "INSIDER_SECRET_LANGUAGE" ||
      value.signal_type === "EXAGGERATED_CERTAINTY" ||
      value.signal_type === "TESTIMONIAL_SOCIAL_PROOF_PRESSURE" ||
      value.signal_type === "UNSUPPORTED_STATISTICAL_CLAIM") &&
    typeof value.matched_text === "string" &&
    typeof value.explanation === "string"
  );
}

function isEvidenceSource(
  value: unknown,
): value is CompleteAnalysisResponse["results"][number]["evidence"][number] {
  if (!isRecord(value) || !isRecord(value.evidence)) return false;
  let validUrl = false;
  try {
    const url = new URL(String(value.url));
    validUrl = url.protocol === "https:" || url.protocol === "http:";
  } catch {
    validUrl = false;
  }
  return (
    typeof value.evidence_id === "string" &&
    typeof value.title === "string" &&
    typeof value.url === "string" &&
    validUrl &&
    typeof value.domain === "string" &&
    (value.source_tier === "tier_1" ||
      value.source_tier === "tier_2" ||
      value.source_tier === "tier_3" ||
      value.source_tier === "tier_4" ||
      value.source_tier === "unknown") &&
    (value.evidence.status === "relevant_evidence_found" ||
      value.evidence.status === "weak_or_partial_evidence" ||
      value.evidence.status === "source_inaccessible" ||
      value.evidence.status === "no_relevant_evidence_found") &&
    (typeof value.evidence.excerpt === "string" || value.evidence.excerpt === null) &&
    (value.evidence.excerpt_source === "search_provider_snippet" ||
      value.evidence.excerpt_source === "demo_fixture" ||
      value.evidence.excerpt_source === "source_page_excerpt" ||
      value.evidence.excerpt_source === null) &&
    (typeof value.published_date === "string" || value.published_date === null) &&
    (value.origin === "live_search" || value.origin === "demo_fixture")
  );
}

function isCompleteAnalysisResponse(
  value: unknown,
): value is CompleteAnalysisResponse {
  if (!isRecord(value) || !Array.isArray(value.results)) return false;
  if (
    typeof value.analysis_id !== "string" ||
    value.status !== "completed" ||
    !Array.isArray(value.manipulation_signals) ||
    !value.manipulation_signals.every(isManipulationSignal)
  ) {
    return false;
  }

  return value.results.every((result: unknown) => {
    if (
      !isRecord(result) ||
      !isRecord(result.claim) ||
      !isRecord(result.assessment) ||
      !Array.isArray(result.evidence) ||
      !Array.isArray(result.manipulation_signals)
    ) {
      return false;
    }
    const { claim, assessment } = result;
    return (
      typeof claim.id === "string" &&
      typeof claim.text === "string" &&
      (claim.kind === "factual" ||
        claim.kind === "financial" ||
        claim.kind === "promotional") &&
      (assessment.assessment === "Supported" ||
        assessment.assessment === "Contradicted" ||
        assessment.assessment === "Unverified" ||
        assessment.assessment === "Needs more evidence") &&
      typeof assessment.rationale === "string" &&
      Array.isArray(assessment.evidence_ids) &&
      assessment.evidence_ids.every((id: unknown) => typeof id === "string") &&
      typeof assessment.uncertainty === "string" &&
      result.evidence.every(isEvidenceSource) &&
      result.manipulation_signals.every(isManipulationSignal)
    );
  });
}

export async function checkBackendHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL.replace(/\/+$/, "")}/health`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Health check returned HTTP ${response.status}.`);
  }

  const body: unknown = await response.json();
  if (
    typeof body !== "object" ||
    body === null ||
    !("status" in body) ||
    body.status !== "ok"
  ) {
    throw new Error("Health check returned an invalid response.");
  }

  return { status: "ok" };
}

export async function analyzeContent(
  request: AnalysisRequest,
): Promise<CompleteAnalysisResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL.replace(/\/+$/, "")}/api/v1/analyze/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      cache: "no-store",
    });
  } catch {
    throw new Error("Could not reach the analysis service. Check the backend and API URL.");
  }

  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 403) {
      throw new Error("Consent is required before external processing can begin.");
    }
    if (response.status === 422) {
      throw new Error(
        "The input could not be processed. Check that it is within the 20,000-character limit.",
      );
    }
    if (response.status === 502) {
      throw new Error(
        "An analysis provider returned an unusable response. No results were displayed.",
      );
    }
    if (response.status === 503) {
      throw new Error(
        "An analysis provider is unavailable or not configured. Please try again later.",
      );
    }
    throw new Error("Analysis failed. Please try again later.");
  }

  if (!isCompleteAnalysisResponse(body)) {
    throw new Error(
      "The analysis service returned a malformed response. No results were displayed.",
    );
  }

  return body;
}

export async function findEvidence(
  claims: ExtractedClaim[],
  consent: boolean,
): Promise<EvidenceResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL.replace(/\/+$/, "")}/api/v1/evidence`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ claims, consent }),
      cache: "no-store",
    });
  } catch {
    throw new Error("Could not reach the evidence search service.");
  }

  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof body.detail === "string"
        ? body.detail
        : `Evidence search failed with HTTP ${response.status}.`;
    throw new Error(detail);
  }

  if (
    typeof body !== "object" ||
    body === null ||
    !("results" in body) ||
    !Array.isArray(body.results) ||
    !("manipulation_signals" in body) ||
    !Array.isArray(body.manipulation_signals) ||
    !body.manipulation_signals.every(
      (signal: unknown) =>
        typeof signal === "object" &&
        signal !== null &&
        "signal_id" in signal &&
        typeof signal.signal_id === "string" &&
        "signal_type" in signal &&
        (signal.signal_type === "GUARANTEED_RETURN" ||
          signal.signal_type === "URGENCY" ||
          signal.signal_type === "SCARCITY_FOMO" ||
          signal.signal_type === "AUTHORITY_CLAIM" ||
          signal.signal_type === "INSIDER_SECRET_LANGUAGE" ||
          signal.signal_type === "EXAGGERATED_CERTAINTY" ||
          signal.signal_type === "TESTIMONIAL_SOCIAL_PROOF_PRESSURE" ||
          signal.signal_type === "UNSUPPORTED_STATISTICAL_CLAIM") &&
        "matched_text" in signal &&
        typeof signal.matched_text === "string" &&
        "explanation" in signal &&
        typeof signal.explanation === "string",
    ) ||
    !body.results.every(
      (result) =>
        typeof result === "object" &&
        result !== null &&
        "claim_id" in result &&
        typeof result.claim_id === "string" &&
        "sources" in result &&
        Array.isArray(result.sources) &&
        result.sources.every(
          (source: unknown) =>
            typeof source === "object" &&
            source !== null &&
            "evidence_id" in source &&
            typeof source.evidence_id === "string" &&
            "title" in source &&
            typeof source.title === "string" &&
            "url" in source &&
            typeof source.url === "string" &&
            "domain" in source &&
            typeof source.domain === "string" &&
            "source_tier" in source &&
            (source.source_tier === "tier_1" ||
              source.source_tier === "tier_2" ||
              source.source_tier === "tier_3" ||
              source.source_tier === "tier_4" ||
              source.source_tier === "unknown") &&
            "evidence" in source &&
            typeof source.evidence === "object" &&
            source.evidence !== null &&
            "status" in source.evidence &&
            (source.evidence.status === "relevant_evidence_found" ||
              source.evidence.status === "weak_or_partial_evidence" ||
              source.evidence.status === "source_inaccessible" ||
              source.evidence.status === "no_relevant_evidence_found") &&
            "excerpt" in source.evidence &&
            (typeof source.evidence.excerpt === "string" ||
              source.evidence.excerpt === null) &&
            "excerpt_source" in source.evidence &&
            (source.evidence.excerpt_source === "search_provider_snippet" ||
              source.evidence.excerpt_source === "demo_fixture" ||
              source.evidence.excerpt_source === null) &&
            "published_date" in source &&
            (typeof source.published_date === "string" ||
              source.published_date === null) &&
            "origin" in source &&
            (source.origin === "live_search" || source.origin === "demo_fixture"),
        ),
    )
  ) {
    throw new Error("The evidence service returned an invalid response.");
  }

  return body as EvidenceResponse;
}
