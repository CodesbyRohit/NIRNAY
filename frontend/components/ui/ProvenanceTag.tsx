import { Icon } from "@/components/ui/Icon";
import { PROVENANCE_COPY, type Provenance } from "@/lib/labels";

/** Marks where a piece of information came from, so users can tell sources from model output. */
export function ProvenanceTag({ kind }: { kind: Provenance }) {
  const copy = PROVENANCE_COPY[kind];
  return (
    <span className={`tag tone-${copy.tone}`}>
      <Icon name={copy.icon} size={13} />
      {copy.label}
    </span>
  );
}
