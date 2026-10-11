import { AssessmentBadge } from "@/components/analysis/AssessmentBadge";
import { EvidenceList } from "@/components/analysis/EvidenceList";
import { NextSteps } from "@/components/analysis/NextSteps";
import { SignalList, uniqueSignals } from "@/components/analysis/SignalList";
import { ProvenanceTag } from "@/components/ui/ProvenanceTag";
import { ASSESSMENT_COPY, CLAIM_KIND_LABELS } from "@/lib/labels";
import { nextStepsFor } from "@/lib/nextSteps";
import type { AssessedClaimResult, ManipulationSignal } from "@/lib/types";

export function ClaimCard({
  result,
  index,
  total,
  contentSignals,
}: {
  result: AssessedClaimResult;
  index: number;
  total: number;
  contentSignals: ManipulationSignal[];
}) {
  const id = `claim-${index + 1}`;
  const state = result.assessment.assessment;
  const copy = ASSESSMENT_COPY[state];
  const claimSignals = uniqueSignals(result.manipulation_signals, contentSignals);

  return (
    <li className="claim-card card" aria-labelledby={`${id}-text`}>
      <header className="claim-head">
        <div className="claim-meta">
          <span className="claim-index">
            Claim {index + 1} of {total}
          </span>
          <span aria-hidden="true">·</span>
          <span>{CLAIM_KIND_LABELS[result.claim.kind]}</span>
        </div>
        <h3 className="claim-text" id={`${id}-text`}>
          “{result.claim.text}”
        </h3>
      </header>

      <div className={`claim-verdict tone-${copy.tone}`}>
        <AssessmentBadge size="lg" state={state} />
        <p className="small-copy">{copy.description}</p>
      </div>

      <section aria-labelledby={`${id}-why`} className="claim-block">
        <div className="block-head">
          <h4 className="heading-sm" id={`${id}-why`}>
            Why this assessment
          </h4>
          <ProvenanceTag kind="ai" />
        </div>
        <p className="body-copy">{result.assessment.rationale}</p>
      </section>

      <EvidenceList id={id} result={result} />

      <section aria-labelledby={`${id}-uncertain`} className="claim-block uncertainty">
        <div className="block-head">
          <h4 className="heading-sm" id={`${id}-uncertain`}>
            What remains uncertain
          </h4>
          <ProvenanceTag kind="ai" />
        </div>
        <p className="body-copy">{result.assessment.uncertainty}</p>
        {(state === "Unverified" || state === "Needs more evidence") && (
          <p className="uncertainty-note">
            This claim has not been established by the available evidence.
          </p>
        )}
      </section>

      {claimSignals.length > 0 && (
        <SignalList
          headingLevel="h4"
          id={`${id}-signals`}
          signals={claimSignals}
          title="Pressure language in this claim"
        />
      )}

      <NextSteps id={id} steps={nextStepsFor(result)} />
    </li>
  );
}
