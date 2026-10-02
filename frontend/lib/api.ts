import type {
  AnalysisRequest,
  CompleteAnalysisResponse,
  EvidenceResponse,
  ExtractedClaim,
  HealthResponse,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

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
    const detail =
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof body.detail === "string"
        ? body.detail
        : `Analysis failed with HTTP ${response.status}.`;
    throw new Error(detail);
  }

  if (
    typeof body !== "object" ||
    body === null ||
    !("analysis_id" in body) ||
    typeof body.analysis_id !== "string" ||
    !("status" in body) ||
    body.status !== "completed" ||
    !("results" in body) ||
    !Array.isArray(body.results) ||
    !body.results.every(
      (result: unknown) =>
        typeof result === "object" &&
        result !== null &&
        "claim" in result &&
        typeof result.claim === "object" &&
        result.claim !== null &&
        "id" in result.claim &&
        typeof result.claim.id === "string" &&
        "text" in result.claim &&
        typeof result.claim.text === "string" &&
        "kind" in result.claim &&
        (result.claim.kind === "factual" ||
          result.claim.kind === "financial" ||
          result.claim.kind === "promotional") &&
        "assessment" in result &&
        typeof result.assessment === "object" &&
        result.assessment !== null &&
        "assessment" in result.assessment &&
        (result.assessment.assessment === "Supported" ||
          result.assessment.assessment === "Contradicted" ||
          result.assessment.assessment === "Unverified" ||
          result.assessment.assessment === "Needs more evidence") &&
        "rationale" in result.assessment &&
        typeof result.assessment.rationale === "string" &&
        "evidence_ids" in result.assessment &&
        Array.isArray(result.assessment.evidence_ids) &&
        result.assessment.evidence_ids.every((id: unknown) => typeof id === "string") &&
        "uncertainty" in result.assessment &&
        typeof result.assessment.uncertainty === "string" &&
        "evidence" in result &&
        Array.isArray(result.evidence) &&
        "manipulation_signals" in result &&
        Array.isArray(result.manipulation_signals) &&
        result.manipulation_signals.every(
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
        ) &&
        result.evidence.every(
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
              source.evidence.excerpt_source === "source_page_excerpt" ||
              source.evidence.excerpt_source === null) &&
            "published_date" in source &&
            (typeof source.published_date === "string" ||
              source.published_date === null) &&
            "origin" in source &&
            (source.origin === "live_search" || source.origin === "demo_fixture"),
        ),
    )
  ) {
    throw new Error("The analysis service returned an invalid response.");
  }

  return body as CompleteAnalysisResponse;
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
