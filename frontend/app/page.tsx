"use client";

import { useEffect, useState } from "react";
import { analyzeContent, checkBackendHealth } from "@/lib/api";
import type { CompleteAnalysisResponse } from "@/lib/types";
import type { ManipulationSignal } from "@/lib/types";

type HealthState =
  | { status: "checking" }
  | { status: "online" }
  | { status: "offline"; message: string };

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

function ManipulationSignals({ signals }: { signals: ManipulationSignal[] }) {
  if (signals.length === 0) return null;

  return (
    <section className="space-y-3 rounded-xl border border-amber-200 bg-amber-50 p-5">
      <h2 className="font-semibold text-amber-950">⚠️ Manipulation signals</h2>
      <p className="text-sm text-amber-900">
        These are language-pattern alerts for investor awareness, not proof of fraud or
        claim truth.
      </p>
      <ul className="space-y-3">
        {signals.map((signal) => (
          <li className="space-y-1" key={signal.signal_id}>
            <p className="font-medium text-amber-950">
              🟠 {SIGNAL_LABELS[signal.signal_type]}
            </p>
            <p className="text-sm text-slate-800">“{signal.matched_text}”</p>
            <p className="text-sm text-slate-700">{signal.explanation}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function Home() {
  const [health, setHealth] = useState<HealthState>({ status: "checking" });
  const [content, setContent] = useState("");
  const [consent, setConsent] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<CompleteAnalysisResponse | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  async function checkHealth() {
    setHealth({ status: "checking" });

    try {
      await checkBackendHealth();
      setHealth({ status: "online" });
    } catch (error) {
      setHealth({
        status: "offline",
        message: error instanceof Error ? error.message : "The health check failed.",
      });
    }
  }

  useEffect(() => {
    void checkHealth();
  }, []);

  async function submitAnalysis(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsAnalyzing(true);
    setAnalysis(null);
    setAnalysisError(null);

    try {
      setAnalysis(await analyzeContent({ content, consent }));
    } catch (error) {
      setAnalysisError(
        error instanceof Error ? error.message : "Analysis could not be completed.",
      );
    } finally {
      setIsAnalyzing(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-6 px-6 py-16">
      <div className="space-y-3">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-700">
          NIRNAY
        </p>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Financial content verification, built on a clear foundation.
        </h1>
        <p className="max-w-2xl text-lg leading-8 text-slate-600">
          Extract separate factual, financial, and promotional claims from pasted content.
        </p>
      </div>

      <section
        className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div>
          <h2 className="font-semibold">Financial content</h2>
          {health.status === "checking" && (
            <p className="mt-1 text-sm text-slate-600">Checking backend health…</p>
          )}
          {health.status === "online" && (
            <p className="mt-1 text-sm text-green-700">Backend is reachable.</p>
          )}
          {health.status === "offline" && (
            <p className="mt-1 text-sm text-red-700">
              Backend is unreachable: {health.message}
            </p>
          )}
        </div>
        <form className="space-y-4" onSubmit={submitAnalysis}>
          <label className="block space-y-2">
            <span className="font-medium">Paste financial content to analyze</span>
            <textarea
              className="min-h-40 w-full resize-y rounded-md border border-slate-300 p-3 leading-6 focus:border-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-200"
              maxLength={20_000}
              onChange={(event) => {
                setContent(event.target.value);
                setAnalysis(null);
                setAnalysisError(null);
              }}
              placeholder="SEBI approved XYZ investment plan. Guaranteed 30% return. Only 200 slots remaining. Join NOW!"
              value={content}
            />
            <span className="block text-right text-sm text-slate-500">
              {content.length.toLocaleString()} / 20,000 characters
            </span>
          </label>
          <label className="flex items-start gap-3 text-sm leading-6 text-slate-700">
            <input
              checked={consent}
              className="mt-1"
              onChange={(event) => setConsent(event.target.checked)}
              type="checkbox"
            />
            <span>
              I consent to sending redacted text to an external AI provider for claim
              extraction, and extracted claims plus retrieved evidence to external
              providers for source retrieval and assessment. The original pasted text is
              not sent for assessment.
            </span>
          </label>
          <button
            className="rounded-md bg-blue-700 px-4 py-2 font-medium text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={!content.trim() || !consent || isAnalyzing}
            type="submit"
          >
            {isAnalyzing ? "Extracting and assessing…" : "Analyze"}
          </button>
        </form>
      </section>

      {isAnalyzing && (
        <p aria-live="polite" className="text-slate-600">
          Extracting claims, retrieving sources, and preparing assessments…
        </p>
      )}
      {analysisError && (
        <p aria-live="assertive" className="rounded-md bg-red-50 p-4 text-red-800">
          {analysisError}
        </p>
      )}
      {analysis && (
        <section aria-live="polite" className="space-y-3">
          <h2 className="text-xl font-semibold">Evidence-grounded results</h2>
          <ManipulationSignals signals={analysis.manipulation_signals} />
          {analysis.results.length === 0 ? (
            <p className="rounded-md border border-slate-200 bg-white p-4 text-slate-600">
              No factual, financial, or promotional claims were identified.
            </p>
          ) : (
            <ol className="space-y-3">
              {analysis.results.map((result, index) => (
                <li
                  className="flex gap-4 rounded-md border border-slate-200 bg-white p-4"
                  key={result.claim.id}
                >
                  <span className="font-semibold text-blue-700">{index + 1}.</span>
                  <div className="w-full space-y-4">
                    <div className="space-y-1">
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Claim
                      </h3>
                      <p>{result.claim.text}</p>
                      <span className="text-sm capitalize text-slate-500">
                        {result.claim.kind}
                      </span>
                    </div>
                    <div className="space-y-1">
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Assessment
                      </h3>
                      <p className="font-semibold">{result.assessment.assessment}</p>
                    </div>
                    <div className="space-y-1">
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Rationale
                      </h3>
                      <p>{result.assessment.rationale}</p>
                    </div>
                    <div className="space-y-1">
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Evidence used
                      </h3>
                      {result.assessment.evidence_ids.length === 0 ? (
                        <p className="text-slate-600">No evidence IDs were used.</p>
                      ) : (
                        <ul className="list-inside list-disc text-sm text-slate-700">
                          {result.assessment.evidence_ids.map((id) => (
                            <li key={id}>{id}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                    <div className="space-y-1">
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Uncertainty
                      </h3>
                      <p>{result.assessment.uncertainty}</p>
                    </div>
                    <ManipulationSignals signals={result.manipulation_signals} />
                    <div className="space-y-2">
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Sources — UNVERIFIED
                      </h3>
                      {result.evidence.length === 0 && (
                        <p className="text-sm text-slate-600">No evidence found.</p>
                      )}
                      {result.evidence.map((source) => (
                        <article
                          className="rounded border border-slate-100 bg-slate-50 p-3 text-sm"
                          key={source.evidence_id}
                        >
                          <p className="mb-2 flex flex-wrap gap-2 text-xs font-semibold uppercase">
                            <span className="rounded bg-slate-200 px-2 py-1">
                              Source tier: {source.source_tier.replace("_", " ")}
                            </span>
                            <span
                              className={`rounded px-2 py-1 ${
                                source.origin === "demo_fixture"
                                  ? "bg-amber-100 text-amber-900"
                                  : "bg-blue-100 text-blue-900"
                              }`}
                            >
                              {source.origin === "demo_fixture"
                                ? "Demo fixture"
                                : "Live search"}
                            </span>
                            {result.assessment.evidence_ids.includes(source.evidence_id) && (
                              <span className="rounded bg-green-100 px-2 py-1 text-green-900">
                                Used in assessment
                              </span>
                            )}
                          </p>
                          <a
                            className="font-medium text-blue-800 underline"
                            href={source.url}
                            rel="noreferrer"
                            target="_blank"
                          >
                            {source.title}
                          </a>
                          <p className="mt-1 text-xs text-slate-500">{source.domain}</p>
                          <p className="mt-2 font-medium text-slate-700">
                            {source.evidence.status.replaceAll("_", " ")}
                          </p>
                          {source.evidence.excerpt && (
                            <>
                              <p className="mt-1 text-slate-700">
                                {source.evidence.excerpt}
                              </p>
                              <p className="mt-1 text-xs text-slate-500">
                                {source.evidence.excerpt_source === "search_provider_snippet"
                                  ? "Search-provider snippet; page not directly retrieved."
                                  : source.evidence.excerpt_source === "demo_fixture"
                                    ? "Illustrative demo fixture; not retrieved page content."
                                    : "Retrieved source-page excerpt."}
                              </p>
                            </>
                          )}
                          {source.published_date && (
                            <p className="mt-1 text-slate-500">
                              Published: {source.published_date}
                            </p>
                          )}
                        </article>
                      ))}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
          <p className="text-sm text-slate-500">
            NIRNAY is informational only. Language-pattern signals are awareness alerts,
            not proof of fraud or truth. No financial action or product is recommended.
          </p>
        </section>
      )}
    </main>
  );
}
