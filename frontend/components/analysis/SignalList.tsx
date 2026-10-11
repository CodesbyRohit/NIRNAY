import { Icon } from "@/components/ui/Icon";
import { ProvenanceTag } from "@/components/ui/ProvenanceTag";
import { SIGNAL_LABELS } from "@/lib/labels";
import type { ManipulationSignal } from "@/lib/types";

export function uniqueSignals(
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

export function SignalList({
  signals,
  title,
  headingLevel = "h3",
  id,
}: {
  signals: ManipulationSignal[];
  title: string;
  headingLevel?: "h3" | "h4";
  id: string;
}) {
  const Heading = headingLevel;

  return (
    <section aria-labelledby={`${id}-heading`} className="signal-panel">
      <div className="block-head">
        <Heading className="heading-sm signal-heading" id={`${id}-heading`}>
          <Icon name="alert" size={16} />
          {title}
        </Heading>
        <ProvenanceTag kind="rule" />
      </div>
      {signals.length === 0 ? (
        <p className="small-copy">No pressure-language patterns were matched.</p>
      ) : (
        <>
          <p className="small-copy">
            Warning signs in the wording, found by fixed rules. They are not proof that
            content is fraudulent or that a claim is false.
          </p>
          <ul className="signal-list">
            {signals.map((signal) => (
              <li className="signal-item" key={signal.signal_id}>
                <p className="signal-name">{SIGNAL_LABELS[signal.signal_type]}</p>
                <blockquote className="signal-quote">“{signal.matched_text}”</blockquote>
                <p className="small-copy">{signal.explanation}</p>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
