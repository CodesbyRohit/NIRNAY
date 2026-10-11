import { AssessmentBadge } from "@/components/analysis/AssessmentBadge";
import { ASSESSMENT_COPY, ASSESSMENT_ORDER } from "@/lib/labels";

export function AssessmentLegend() {
  return (
    <details className="aside-card legend">
      <summary className="legend-summary">
        <span className="heading-sm">What the labels mean</span>
      </summary>
      <dl className="legend-list">
        {ASSESSMENT_ORDER.map((state) => (
          <div key={state}>
            <dt>
              <AssessmentBadge state={state} />
            </dt>
            <dd className="small-copy">{ASSESSMENT_COPY[state].description}</dd>
          </div>
        ))}
      </dl>
      <p className="small-copy legend-note">
        Labels are qualitative. NIRNAY does not report a confidence percentage or a
        probability that a claim is true.
      </p>
      <p className="small-copy">
        An AI model proposes each label, and fixed rules then check it. A model cannot mark
        a claim Supported or Contradicted without citing retrieved page text; if it tries,
        the rules change the label to Needs more evidence and replace the explanation.
        Claims with no retrieved sources are marked Unverified without using a model.
      </p>
    </details>
  );
}
