"use client";

import { useEffect, useState } from "react";

export function ProgressPanel({
  includesOcr,
  previewLabel,
  previewText,
}: {
  includesOcr: boolean;
  previewLabel: string;
  previewText: string;
}) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const timer = window.setInterval(
      () => setElapsed(Math.floor((Date.now() - started) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, []);

  const steps = [
    ...(includesOcr ? ["Reading text from the screenshot"] : []),
    "Separating the content into claims",
    "Finding sources for each claim",
    "Assessing each claim against its sources",
    "Checking the wording for pressure language",
  ];

  return (
    <section aria-busy="true" aria-labelledby="progress-heading" className="progress-view">
      <div className="card card-raised progress-card">
        <div className="progress-head">
          <p className="eyebrow">Analysis in progress</p>
          <h2 className="heading-lg" id="progress-heading">
            Checking your content
          </h2>
          <p className="body-copy">
            The service does not report step-by-step progress, so no step is marked as
            done until all results arrive. Time depends on how many claims are found and
            how quickly the providers respond.
          </p>
        </div>

        <div aria-hidden="true" className="progress-track">
          <span className="progress-bar" />
        </div>
        <p className="small-copy tabular-nums">Elapsed: {elapsed} s</p>

        <div>
          <h3 className="heading-sm">What happens during analysis</h3>
          <ul className="progress-steps">
            {steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ul>
        </div>
      </div>

      <section aria-labelledby="pending-heading" className="aside-card">
        <h3 className="aside-title" id="pending-heading">
          {previewLabel}
        </h3>
        <p className="submitted-text">{previewText}</p>
      </section>
    </section>
  );
}
