"use client";

import { useEffect, useRef, useState } from "react";
import {
  AnalysisForm,
  DEMO_CONTENT,
  type InputMode,
} from "@/components/analysis/AnalysisForm";
import { HowItWorks } from "@/components/analysis/HowItWorks";
import { SiteFooter } from "@/components/analysis/SiteFooter";
import { SiteHeader, type HealthState } from "@/components/analysis/SiteHeader";
import { TrustPanels } from "@/components/analysis/TrustPanels";
import { Icon } from "@/components/ui/Icon";
import { analyzeContent, analyzeScreenshot, checkBackendHealth } from "@/lib/api";
import type {
  AssessmentState,
  CompleteAnalysisResponse,
  EvidenceSource,
  ManipulationSignal,
} from "@/lib/types";

const MAX_SCREENSHOT_BYTES = 10 * 1024 * 1024;

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
  contentLabel,
}: {
  analysis: CompleteAnalysisResponse;
  analyzedContent: string;
  contentLabel: string;
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
          <h3>{contentLabel}</h3>
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
  const [inputMode, setInputMode] = useState<InputMode>("text");
  const [screenshotFile, setScreenshotFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<CompleteAnalysisResponse | null>(null);
  const [analyzedContent, setAnalyzedContent] = useState("");
  const [analyzedContentLabel, setAnalyzedContentLabel] = useState("Analyzed content");
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const screenshotInputRef = useRef<HTMLInputElement>(null);

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

    if (inputMode === "text" && !content.trim()) {
      setFormError("Paste financial content before starting an analysis.");
      return;
    }
    if (inputMode === "screenshot" && !screenshotFile) {
      setFormError("Choose a screenshot before starting an analysis.");
      return;
    }
    if (
      inputMode === "screenshot" &&
      screenshotFile &&
      screenshotFile.size > MAX_SCREENSHOT_BYTES
    ) {
      setFormError("This image exceeds the 10 MiB upload limit.");
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
      if (inputMode === "screenshot" && screenshotFile) {
        const result = await analyzeScreenshot(screenshotFile, consent);
        setAnalysis(result.analysis);
        setAnalyzedContent(result.ocr_text);
        setAnalyzedContentLabel("Redacted OCR text");
        setScreenshotFile(null);
        if (screenshotInputRef.current) screenshotInputRef.current.value = "";
      } else {
        const result = await analyzeContent({ content, consent });
        setAnalysis(result);
        setAnalyzedContent(content.trim());
        setAnalyzedContentLabel("Analyzed content");
      }
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

  function updateScreenshot(file: File | null) {
    setScreenshotFile(file);
    setAnalysis(null);
    setAnalyzedContent("");
    setAnalysisError(null);
    setFormError(null);
    if (!file && screenshotInputRef.current) screenshotInputRef.current.value = "";
  }

  return (
    <>
      <SiteHeader health={health} />
      <main className="page-shell" id="main" tabIndex={-1}>
        <section aria-labelledby="page-title" className="hero" id="top">
          <div className="hero-copy">
            <p className="eyebrow">For forwarded tips, ads, and posts about money</p>
            <h1 className="display" id="page-title">
              Check the claim before you trust the message.
            </h1>
            <p className="lede">
              NIRNAY separates financial content into individual claims, looks for sources,
              and shows what the evidence can — and cannot — establish.
            </p>
            <ul className="hero-points">
              <li>
                <Icon name="document" size={18} />
                Every source shown with its website, date, and an excerpt
              </li>
              <li>
                <Icon name="model" size={18} />
                AI-written assessments are clearly labelled
              </li>
              <li>
                <Icon name="compass" size={18} />
                Uncertainty and next checks are shown, not hidden
              </li>
            </ul>
          </div>

          <AnalysisForm
            consent={consent}
            content={content}
            formError={formError}
            health={health}
            inputMode={inputMode}
            isAnalyzing={isAnalyzing}
            onConsentChange={(value) => {
              setConsent(value);
              setFormError(null);
            }}
            onContentChange={updateContent}
            onInputModeChange={(mode) => {
              setInputMode(mode);
              setFormError(null);
            }}
            onLoadExample={() => {
              setInputMode("text");
              updateContent(DEMO_CONTENT);
            }}
            onScreenshotChange={updateScreenshot}
            onSubmit={submitAnalysis}
            screenshotFile={screenshotFile}
            screenshotInputRef={screenshotInputRef}
          />
        </section>

        {isAnalyzing && (
          <section
            aria-busy="true"
            aria-labelledby="progress-heading"
            className="progress-card"
            role="status"
          >
            <h2 id="progress-heading">Analysis in progress</h2>
            <p>The analysis service does not report live progress for individual steps.</p>
          </section>
        )}

        {analysisError && (
          <section aria-labelledby="error-heading" className="error-card" role="alert">
            <h2 id="error-heading">Your results are not available</h2>
            <p>{analysisError}</p>
          </section>
        )}

        {analysis && (
          <AnalysisResults
            analysis={analysis}
            analyzedContent={analyzedContent}
            contentLabel={analyzedContentLabel}
          />
        )}

        <HowItWorks />
        <TrustPanels />
      </main>
      <SiteFooter />
    </>
  );
}
