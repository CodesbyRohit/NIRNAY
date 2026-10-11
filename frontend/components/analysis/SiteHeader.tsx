export type HealthState = "checking" | "online" | "offline";

const HEALTH_COPY: Record<HealthState, string> = {
  checking: "Connecting to analysis service",
  online: "Analysis service connected",
  offline: "Analysis service unavailable",
};

export function SiteHeader({ health }: { health: HealthState }) {
  return (
    <header className="site-header">
      <div className="page-shell site-header-inner">
        <a aria-label="NIRNAY home" className="brand" href="#top">
          <span aria-hidden="true" className="brand-mark">
            N
          </span>
          <span className="brand-text">
            <span className="brand-name">NIRNAY</span>
            <span className="brand-tagline">Financial content check</span>
          </span>
        </a>
        <p aria-live="polite" className={`service-status status-${health}`}>
          <span aria-hidden="true" className="status-dot" />
          {HEALTH_COPY[health]}
        </p>
      </div>
    </header>
  );
}
