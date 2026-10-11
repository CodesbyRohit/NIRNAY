import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/components/ui/Icon";
import { ProvenanceTag } from "@/components/ui/ProvenanceTag";
import { formatPublishedDate } from "@/lib/evidence";
import { EVIDENCE_STATUS_COPY, TIER_COPY, excerptSourceLabel } from "@/lib/labels";
import type { EvidenceSource } from "@/lib/types";

export function EvidenceCard({ source }: { source: EvidenceSource }) {
  const tier = TIER_COPY[source.source_tier];
  const status = EVIDENCE_STATUS_COPY[source.evidence.status];
  const isDemo = source.origin === "demo_fixture";

  return (
    <article className={`evidence-card ${isDemo ? "evidence-card-demo" : ""}`}>
      <div className="evidence-top">
        <span className="evidence-domain">
          <Icon name="globe" size={14} />
          {source.domain}
        </span>
        <ProvenanceTag kind={isDemo ? "demo" : "live"} />
      </div>

      <h6 className="evidence-title">
        <a href={source.url} rel="noopener noreferrer" target="_blank">
          {source.title}
          <Icon className="evidence-title-icon" name="external" size={14} />
          <span className="sr-only"> (opens in a new tab)</span>
        </a>
      </h6>

      <dl className="evidence-facts">
        <div>
          <dt>Source type</dt>
          <dd>
            <strong>{tier.label}</strong> · {tier.description}
          </dd>
        </div>
        <div>
          <dt>Published</dt>
          <dd>
            {source.published_date ? (
              <span className="inline-flex items-center gap-1">
                <Icon name="calendar" size={13} />
                {formatPublishedDate(source.published_date)}
              </span>
            ) : (
              "Date not provided"
            )}
          </dd>
        </div>
        <div>
          <dt>Match with claim</dt>
          <dd>
            <Badge tone={status.tone}>{status.label}</Badge>
          </dd>
        </div>
      </dl>

      {source.evidence.excerpt ? (
        <figure className="evidence-excerpt">
          <blockquote>{source.evidence.excerpt}</blockquote>
          <figcaption>{excerptSourceLabel(source.evidence.excerpt_source)}</figcaption>
        </figure>
      ) : (
        <p className="small-copy evidence-no-excerpt">
          No excerpt was available for this source. {status.description}
        </p>
      )}

      <p className="evidence-url" title={source.url}>
        {source.url}
      </p>
    </article>
  );
}
