"use client";

import { useEffect, useRef, useState } from "react";
import {
  AnalysisForm,
  DEMO_CONTENT,
  type InputMode,
} from "@/components/analysis/AnalysisForm";
import { HowItWorks } from "@/components/analysis/HowItWorks";
import { ResultsWorkspace } from "@/components/analysis/ResultsWorkspace";
import { SiteFooter } from "@/components/analysis/SiteFooter";
import { SiteHeader, type HealthState } from "@/components/analysis/SiteHeader";
import { TrustPanels } from "@/components/analysis/TrustPanels";
import { Icon } from "@/components/ui/Icon";
import { analyzeContent, analyzeScreenshot, checkBackendHealth } from "@/lib/api";
import type { CompleteAnalysisResponse } from "@/lib/types";

const MAX_SCREENSHOT_BYTES = 10 * 1024 * 1024;

function friendlyError(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Analysis could not be completed. Please try again.";
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
  const resultsHeadingRef = useRef<HTMLHeadingElement>(null);

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

  useEffect(() => {
    if (analysis) {
      window.scrollTo({ top: 0 });
      resultsHeadingRef.current?.focus();
    }
  }, [analysis]);

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

  function returnToInput() {
    // Keeps the pasted text so it can be edited and re-analyzed.
    setAnalysis(null);
    setAnalyzedContent("");
    window.scrollTo({ top: 0 });
    requestAnimationFrame(() => {
      document
        .getElementById(inputMode === "text" ? "financial-content" : "screenshot-file")
        ?.focus();
    });
  }

  return (
    <>
      <SiteHeader health={health} />
      <main className="page-shell" id="main" tabIndex={-1}>
        {analysis ? (
          <ResultsWorkspace
            analysis={analysis}
            analyzedContent={analyzedContent}
            contentLabel={analyzedContentLabel}
            headingRef={resultsHeadingRef}
            onEdit={returnToInput}
          />
        ) : (
          <>
            <section aria-labelledby="page-title" className="hero" id="top">
              <div className="hero-copy">
                <p className="eyebrow">For forwarded tips, ads, and posts about money</p>
                <h1 className="display" id="page-title">
                  Check the claim before you trust the message.
                </h1>
                <p className="lede">
                  NIRNAY separates financial content into individual claims, looks for
                  sources, and shows what the evidence can — and cannot — establish.
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

              <div className="hero-form">
                {isAnalyzing && (
                  <section
                    aria-busy="true"
                    aria-labelledby="progress-heading"
                    className="progress-card"
                    role="status"
                  >
                    <h2 id="progress-heading">Analysis in progress</h2>
                    <p>
                      The analysis service does not report live progress for individual
                      steps.
                    </p>
                  </section>
                )}

                {analysisError && (
                  <section
                    aria-labelledby="error-heading"
                    className="error-card"
                    role="alert"
                  >
                    <h2 id="error-heading">Your results are not available</h2>
                    <p>{analysisError}</p>
                  </section>
                )}

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
              </div>
            </section>

            <HowItWorks />
            <TrustPanels />
          </>
        )}
      </main>
      <SiteFooter />
    </>
  );
}
