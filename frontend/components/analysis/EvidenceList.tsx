import { AssessmentBadge } from "@/components/analysis/AssessmentBadge";
import { EvidenceCard } from "@/components/analysis/EvidenceCard";
import { ProvenanceTag } from "@/components/ui/ProvenanceTag";
import { groupEvidence } from "@/lib/evidence";
import type { AssessedClaimResult } from "@/lib/types";

export function EvidenceList({
  result,
  id,
}: {
  result: AssessedClaimResult;
  id: string;
}) {
  const { cited, uncited } = groupEvidence(result);
  const total = result.evidence.length;

  return (
    <section aria-labelledby={`${id}-evidence`} className="claim-block">
      <div className="block-head">
        <h4 className="heading-sm" id={`${id}-evidence`}>
          Evidence
          <span className="block-count">
            {total === 0 ? "none retrieved" : `${total} source${total === 1 ? "" : "s"}`}
          </span>
        </h4>
        <ProvenanceTag kind="source" />
      </div>

      {total === 0 ? (
        <p className="empty-inline">
          No sources were retrieved for this claim. When there is no evidence, NIRNAY marks
          the claim Unverified without asking a model to judge it. That does not mean the
          claim is false.
        </p>
      ) : (
        <div className="evidence-groups">
          {cited.length > 0 ? (
            <div className="evidence-group">
              <div className="evidence-group-head">
                <h5 className="evidence-group-title">Cited in this assessment</h5>
                <AssessmentBadge state={result.assessment.assessment} />
              </div>
              <p className="small-copy">
                The assessment referred to these sources when reaching its label.
              </p>
              <ul className="evidence-list">
                {cited.map((source) => (
                  <li key={source.evidence_id}>
                    <EvidenceCard source={source} />
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="empty-inline">
              The assessment did not cite any of the retrieved sources.
            </p>
          )}

          {uncited.length > 0 && (
            <div className="evidence-group">
              <div className="evidence-group-head">
                <h5 className="evidence-group-title">Also retrieved, not cited</h5>
              </div>
              <p className="small-copy">
                Found by search but not used to reach the assessment. Shown so you can
                review them yourself.
              </p>
              <ul className="evidence-list">
                {uncited.map((source) => (
                  <li key={source.evidence_id}>
                    <EvidenceCard source={source} />
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
