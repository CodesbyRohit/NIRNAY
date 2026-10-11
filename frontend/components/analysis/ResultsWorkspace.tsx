import type { Ref } from "react";
import { AssessmentBadge } from "@/components/analysis/AssessmentBadge";
import { AssessmentLegend } from "@/components/analysis/AssessmentLegend";
import { ClaimCard } from "@/components/analysis/ClaimCard";
import { ContentSummary } from "@/components/analysis/ContentSummary";
import { DemoBanner } from "@/components/analysis/DemoBanner";
import { SignalList } from "@/components/analysis/SignalList";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { countAssessments, hasDemoEvidence } from "@/lib/evidence";
import { ASSESSMENT_ORDER } from "@/lib/labels";
import type { CompleteAnalysisResponse } from "@/lib/types";

export function ResultsWorkspace({
  analysis,
  analyzedContent,
  contentLabel,
  onEdit,
  headingRef,
}: {
  analysis: CompleteAnalysisResponse;
  analyzedContent: string;
  contentLabel: string;
  onEdit: () => void;
  headingRef?: Ref<HTMLHeadingElement>;
}) {
  const claimCount = analysis.results.length;
  const evidenceCount = analysis.results.reduce(
    (total, result) => total + result.evidence.length,
    0,
  );
  const counts = countAssessments(analysis);

  return (
    <section aria-labelledby="results-heading" className="workspace">
      <div className="workspace-bar">
        <Button onClick={onEdit} variant="secondary">
          <Icon name="arrowLeft" size={16} />
          Edit or check something else
        </Button>
      </div>

      <header className="workspace-head">
        <p className="eyebrow">Analysis results</p>
        <h2 className="heading-lg" id="results-heading" ref={headingRef} tabIndex={-1}>
          What the evidence shows
        </h2>
        <p className="body-copy">
          Each claim is assessed separately, using only the sources retrieved for it.
          Assessments can be wrong or incomplete, so open the sources and check them
          yourself.
        </p>
      </header>

      {hasDemoEvidence(analysis) && <DemoBanner />}

      <div className="workspace-grid">
        <aside aria-label="Analysis overview" className="workspace-aside">
          <ContentSummary label={contentLabel} text={analyzedContent} />

          <section aria-labelledby="overview-heading" className="aside-card">
            <h3 className="aside-title" id="overview-heading">
              Overview
            </h3>
            <dl className="overview-counts">
              <div>
                <dt>Claims</dt>
                <dd>{claimCount}</dd>
              </div>
              <div>
                <dt>Sources</dt>
                <dd>{evidenceCount}</dd>
              </div>
              <div>
                <dt>Signals</dt>
                <dd>{analysis.manipulation_signals.length}</dd>
              </div>
            </dl>
            {claimCount > 0 && (
              <ul aria-label="Claims by assessment" className="overview-states">
                {ASSESSMENT_ORDER.filter((state) => counts[state] > 0).map((state) => (
                  <li key={state}>
                    <AssessmentBadge state={state} />
                    <span className="tabular-nums">× {counts[state]}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <SignalList
            id="content-signals"
            signals={analysis.manipulation_signals}
            title="Pressure language in the content"
          />

          <AssessmentLegend />
        </aside>

        <div className="workspace-main">
          {claimCount === 0 ? (
            <section className="card empty-state">
              <h3 className="heading-md">No claims were extracted</h3>
              <p className="body-copy">
                The analysis did not find a factual, financial, or promotional claim in
                this content. Try pasting the specific statement you want to check, for
                example a promised return or an approval it mentions.
              </p>
            </section>
          ) : (
            <ol aria-label="Claim assessments" className="claim-list">
              {analysis.results.map((result, index) => (
                <ClaimCard
                  contentSignals={analysis.manipulation_signals}
                  index={index}
                  key={result.claim.id}
                  result={result}
                  total={claimCount}
                />
              ))}
            </ol>
          )}

          <p className="results-footnote">
            NIRNAY is an information tool. It does not recommend financial actions or
            products, or predict investment returns. Before acting, confirm important claims
            directly with the original source or the relevant regulator.
          </p>
        </div>
      </div>
    </section>
  );
}
