"use client";

import { useEffect, useState } from "react";
import { analyzeContent, checkBackendHealth } from "@/lib/api";
import type {
  AssessmentState,
  CompleteAnalysisResponse,
  EvidenceSource,
  ManipulationSignal,
} from "@/lib/types";

type HealthState = "checking" | "online" | "offline";

const DEMO_CONTENT =
  "SEBI approved XYZ investment plan. Guaranteed 30% return. Only 200 slots remaining. Join NOW!";

const SIGNAL_LABELS: Record<ManipulationSignal["signal_type"], string> = {
  GUARANTEED_RETURN: "Guaranteed-return language",
  URGENCY: "Urgency",
  SCARCITY_FOMO: "Scarcity / FOMO",
  AUTHORITY_CLAIM: "Authority claim",
  INSIDER_SECRET_LANGUAGE: "Insider / secret language",
  EXAGGERATED_CERTAINTY: "Exaggerated certainty",
  TESTIMONIAL_SOCIAL_PROOF_PRESSURE: "Testimonial / social-proof pressure",
  UNSUPPORTED_STATISTICAL_CLAIM: "Promotional numerical claim",
};

const ASSESSMENT_STYLES: Record<AssessmentState, string> = {
  Supported: "border-teal-300 bg-teal-50 text-teal-950",
  Contradicted: "border-rose-300 bg-rose-50 text-rose-950",
  Unverified: "border-slate-300 bg-slate-100 text-slate-900",
  "Needs more evidence": "border-amber-300 bg-amber-50 text-amber-950",
};

function uniqueSignals(
  signals: ManipulationSignal[],
  alreadyShown: ManipulationSignal[] = [],
): ManipulationSignal[] {
  const existing = new Set(
    alreadyShown.map(
      (signal) => `${signal.signal_type}:${signal.matched_text.toLocaleLowerCase()}`,
    ),
  );
  return signals.filter((signal) => {
    const key = `${signal.signal_type}:${signal.matched_text.toLocaleLowerCase()}`;
    if (existing.has(key)) return false;
    existing.add(key);
    return true;
  });
}

function SignalList({
  signals,
  title = "Manipulation signals",
}: {
  signals: ManipulationSignal[];
  title?: string;
}) {
  const headingId = title.toLowerCase().replace(/[^a-z0-9]+/g, "-");

  return (
    <section aria-labelledby={`${headingId}-heading`} className="signal-panel">
      <div className="section-heading">
        <span aria-hidden="true" className="signal-mark">
          !
        </span>
        <h3 id={`${headingId}-heading`}>{title}</h3>
      </div>
      {signals.length === 0 ? (
        <p className="muted-copy">No manipulation signals were identified.</p>
      ) : (
        <>
          <p className="signal-disclaimer">
            Manipulation signals are warning signs in the language. They are not proof
            that content is fraudulent or that a claim is false.
          </p>
          <ul className="signal-list">
            {signals.map((signal) => (
              <li className="signal-item" key={signal.signal_id}>
                <p className="signal-name">{SIGNAL_LABELS[signal.signal_type]}</p>
                <blockquote>“{signal.matched_text}”</blockquote>
                <p className="muted-copy">{signal.explanation}</p>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function excerptLabel(source: EvidenceSource["evidence"]["excerpt_source"]): string {
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

function EvidenceCard({
  source,
  cited,
}: {
  source: EvidenceSource;
  cited: boolean;
}) {
  return (
    <article className="evidence-card">
      <div className="evidence-meta">
        <span className="source-tier">
          Source tier: {source.source_tier.replaceAll("_", " ")}
        </span>
        <span
          className={`origin-tag ${
            source.origin === "demo_fixture" ? "origin-demo" : "origin-live"
          }`}
        >
          {source.origin === "demo_fixture" ? "Demo fixture" : "Live search"}
        </span>
        {cited && <span className="citation-tag">Used in assessment</span>}
      </div>
      <h4 className="evidence-title">
        <a href={source.url} rel="noreferrer" target="_blank">
          {source.title}
        </a>
      </h4>
      <p className="evidence-domain">{source.domain}</p>
      <p className="evidence-status">
        Evidence status: {source.evidence.status.replaceAll("_", " ")}
      </p>
      {source.evidence.excerpt ? (
        <blockquote className="evidence-excerpt">
          {source.evidence.excerpt}
        </blockquote>
      ) : (
        <p className="muted-copy">No excerpt was available for this source.</p>
      )}
      <p className="excerpt-source">{excerptLabel(source.evidence.excerpt_source)}</p>
      {source.published_date && (
        <p className="evidence-date">Publication date: {source.published_date}</p>
      )}
      <a className="source-link" href={source.url} rel="noreferrer" target="_blank">
        Open source <span aria-hidden="true">↗</span>
      </a>
    </article>
  );
}

function friendlyError(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Analysis could not be completed. Please try again.";
}

function AnalysisResults({
  analysis,
  analyzedContent,
}: {
  analysis: CompleteAnalysisResponse;
  analyzedContent: string;
}) {
  const claimCount = analysis.results.length;
  const evidenceCount = analysis.results.reduce(
    (total, result) => total + result.evidence.length,
    0,
  );

  return (
    <section aria-labelledby="results-heading" className="results-section">
      <div className="results-intro">
        <p className="eyebrow">Investigation results</p>
        <h2 id="results-heading">What the analysis found</h2>
        <p>
          Each claim is considered separately against the evidence returned. Assessments
          can be uncertain; review the cited sources directly.
        </p>
      </div>

      <section aria-label="Analysis summary" className="summary-card">
        <div className="summary-copy">
          <h3>Analyzed content</h3>
          <p className="content-summary">{analyzedContent}</p>
        </div>
        <dl className="summary-counts">
          <div>
            <dt>Claims</dt>
            <dd>{claimCount}</dd>
          </div>
          <div>
            <dt>Evidence items</dt>
            <dd>{evidenceCount}</dd>
          </div>
          <div>
            <dt>Content-level signals</dt>
            <dd>{analysis.manipulation_signals.length}</dd>
          </div>
        </dl>
        <p className="summary-caveat">
          These results organize available information; they do not replace checking
          important claims with their original sources.
        </p>
      </section>

      <SignalList
        signals={analysis.manipulation_signals}
        title="Content-level signals"
      />

      {claimCount === 0 ? (
        <section className="empty-state" role="status">
          <h3>No claims extracted</h3>
          <p>
            The analysis did not identify a factual, financial, or promotional claim in
            this text. Try pasting a specific statement to examine.
          </p>
        </section>
      ) : (
        <ol aria-label="Claim assessments" className="claim-list">
          {analysis.results.map((result, index) => {
            const claimSignals = uniqueSignals(
              result.manipulation_signals,
              analysis.manipulation_signals,
            );
            const relevantEvidence = result.evidence.filter(
              (source) => source.evidence.status === "relevant_evidence_found",
            );

            return (
              <li className="claim-card" key={result.claim.id}>
                <div className="claim-number" aria-hidden="true">
                  {String(index + 1).padStart(2, "0")}
                </div>
                <div className="claim-content">
                  <section className="claim-section">
                    <p className="eyebrow">Claim · {result.claim.kind}</p>
                    <h3 className="claim-text">{result.claim.text}</h3>
                  </section>

                  <section aria-label="Assessment" className="claim-section">
                    <p className="eyebrow">Assessment</p>
                    <p
                      className={`assessment-badge ${ASSESSMENT_STYLES[result.assessment.assessment]}`}
                    >
                      {result.assessment.assessment}
                    </p>
                  </section>

                  <section className="claim-section">
                    <h4 className="subheading">Why</h4>
                    <p className="body-copy">{result.assessment.rationale}</p>
                  </section>

                  <section className="claim-section">
                    <div className="section-heading">
                      <h4 className="subheading">Evidence</h4>
                      {relevantEvidence.length === 0 && (
                        <span className="muted-copy">No relevant evidence identified</span>
                      )}
                    </div>
                    {result.evidence.length === 0 ? (
                      <p className="empty-inline">
                        No evidence items were returned for this claim.
                      </p>
                    ) : (
                      <ul className="evidence-list">
                        {result.evidence.map((source) => (
                          <li key={source.evidence_id}>
                            <EvidenceCard
                              cited={result.assessment.evidence_ids.includes(
                                source.evidence_id,
                              )}
                              source={source}
                            />
                          </li>
                        ))}
                      </ul>
                    )}
                  </section>

                  <section className="uncertainty-panel">
                    <h4 className="subheading">Uncertainty</h4>
                    <p className="body-copy">{result.assessment.uncertainty}</p>
                    {(result.assessment.assessment === "Unverified" ||
                      result.assessment.assessment === "Needs more evidence") && (
                      <p className="uncertainty-note">
                        This claim has not been established by the available evidence.
                      </p>
                    )}
                  </section>

                  {claimSignals.length > 0 && (
                    <SignalList signals={claimSignals} title="Claim-level signals" />
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}

      <section aria-labelledby="pause-heading" className="pause-card">
        <div aria-hidden="true" className="pause-icon">
          ⏸
        </div>
        <div>
          <h3 id="pause-heading">PAUSE &amp; VERIFY</h3>
          <p>
            Before acting, verify important claims directly with the cited authoritative
            source.
          </p>
        </div>
      </section>
      <p className="results-footnote">
        NIRNAY is an informational tool. It does not recommend financial actions or
        products, or predict investment returns.
      </p>
    </section>
  );
}

export default function Home() {
  const [health, setHealth] = useState<HealthState>("checking");
  const [content, setContent] = useState("");
  const [consent, setConsent] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<CompleteAnalysisResponse | null>(null);
  const [analyzedContent, setAnalyzedContent] = useState("");
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    void checkBackendHealth()
      .then(() => {
        if (mounted) setHealth("online");
      })
      .catch(() => {
        if (mounted) setHealth("offline");
      });
    return () => {
      mounted = false;
    };
  }, []);

  async function submitAnalysis(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAnalysisError(null);

    if (!content.trim()) {
      setFormError("Paste financial content before starting an analysis.");
      return;
    }
    if (!consent) {
      setFormError("Please provide consent for external processing to continue.");
      return;
    }

    setFormError(null);
    setIsAnalyzing(true);
    setAnalysis(null);
    setAnalyzedContent("");

    try {
      const result = await analyzeContent({ content, consent });
      setAnalysis(result);
      setAnalyzedContent(content.trim());
    } catch (error) {
      setAnalysisError(friendlyError(error));
    } finally {
      setIsAnalyzing(false);
    }
  }

  function updateContent(value: string) {
    setContent(value);
    setAnalysis(null);
    setAnalyzedContent("");
    setAnalysisError(null);
    setFormError(null);
  }

  return (
    <main className="page-shell">
      <header className="site-header">
        <a aria-label="NIRNAY home" className="brand" href="#top">
          <span aria-hidden="true" className="brand-mark">
            N
          </span>
          <span>NIRNAY</span>
        </a>
        <div aria-live="polite" className={`service-status status-${health}`}>
          <span aria-hidden="true" className="status-dot" />
          {health === "checking"
            ? "Connecting to analysis service"
            : health === "online"
              ? "Analysis service connected"
              : "Analysis service unavailable"}
        </div>
      </header>

      <section aria-labelledby="page-title" className="hero" id="top">
        <p className="eyebrow">A clearer way to check financial claims</p>
        <h1 id="page-title">Verify before you trust.</h1>
        <p className="hero-copy">
          Check financial content against evidence before acting on it.
        </p>
        <p className="hero-detail">
          NIRNAY separates claims, finds sources, and shows what the available evidence
          can—and cannot—establish.
        </p>
      </section>

      <section aria-labelledby="input-heading" className="input-card">
        <div className="card-heading">
          <div>
            <p className="eyebrow">Start an investigation</p>
            <h2 id="input-heading">What would you like to check?</h2>
          </div>
          <span className="privacy-chip">
            <span aria-hidden="true">⌑</span> No saved history
          </span>
        </div>
        <form noValidate onSubmit={submitAnalysis}>
          <label className="field-label" htmlFor="financial-content">
            Paste financial content
          </label>
          <textarea
            aria-describedby="content-help content-count"
            className="content-input"
            id="financial-content"
            maxLength={20_000}
            onChange={(event) => updateContent(event.target.value)}
            placeholder="Paste a message, post, advertisement, or financial claim here…"
            value={content}
          />
          <div className="input-meta">
            <p id="content-help">
              Up to 20,000 characters. Avoid adding personal account or contact details.
            </p>
            <p id="content-count" aria-live="off">
              {content.length.toLocaleString()} / 20,000
            </p>
          </div>

          <div className="demo-row">
            <button
              className="text-button"
              onClick={() => updateContent(DEMO_CONTENT)}
              type="button"
            >
              Load illustrative example
            </button>
            <p>
              <span className="demo-content">“{DEMO_CONTENT}”</span> Fictional
              demonstration only; XYZ is not presented as a real investment product.
            </p>
          </div>

          <label className="consent-row">
            <input
              checked={consent}
              className="consent-checkbox"
              onChange={(event) => {
                setConsent(event.target.checked);
                setFormError(null);
              }}
              type="checkbox"
            />
            <span>
              I consent to sending redacted text to an external AI provider for claim
              extraction, and extracted claims plus retrieved evidence to external
              providers for source retrieval and assessment.
            </span>
          </label>
          <p className="privacy-note">
            Obvious personal identifiers are redacted locally. The original text is not
            sent to the assessment provider or saved by NIRNAY; external providers
            process the redacted text, claims, or evidence as described above.
          </p>

          {formError && (
            <p className="form-message form-error" role="alert">
              {formError}
            </p>
          )}
          <div className="submit-row">
            <button
              aria-busy={isAnalyzing}
              className="analyze-button"
              disabled={isAnalyzing}
              type="submit"
            >
              {isAnalyzing ? "Analyzing…" : "Analyze content"}
              {!isAnalyzing && <span aria-hidden="true">→</span>}
            </button>
            <p>Analysis is informational and does not provide investment advice.</p>
          </div>
        </form>
      </section>

      {isAnalyzing && (
        <section
          aria-busy="true"
          aria-labelledby="progress-heading"
          className="progress-card"
          role="status"
        >
          <div className="progress-title">
            <span aria-hidden="true" className="loading-spinner" />
            <div>
              <h2 id="progress-heading">Analysis in progress</h2>
              <p>The analysis service does not report live progress for individual steps.</p>
            </div>
          </div>
          <ol className="progress-steps">
            <li>Extracting claims</li>
            <li>Finding evidence</li>
            <li>Assessing claims</li>
            <li>Detecting manipulation signals</li>
          </ol>
        </section>
      )}

      {analysisError && (
        <section aria-labelledby="error-heading" className="error-card" role="alert">
          <p className="eyebrow">Unable to complete analysis</p>
          <h2 id="error-heading">Your results are not available</h2>
          <p>{analysisError}</p>
          <p className="muted-copy">
            Your content remains in this page only. You can retry when the service is
            available.
          </p>
          <button
            className="text-button"
            onClick={() => setAnalysisError(null)}
            type="button"
          >
            Dismiss message
          </button>
        </section>
      )}

      {analysis && (
        <AnalysisResults analysis={analysis} analyzedContent={analyzedContent} />
      )}

      <footer className="site-footer">
        <p>NIRNAY · Financial information awareness</p>
        <p>Review evidence, keep uncertainty visible, and verify sources directly.</p>
      </footer>
    </main>
  );
}
