import { Icon } from "@/components/ui/Icon";

export function TrustPanels() {
  return (
    <section aria-label="Privacy and responsible use" className="trust-grid">
      <article className="trust-panel">
        <div className="trust-panel-head">
          <span aria-hidden="true" className="trust-icon">
            <Icon name="lock" size={20} />
          </span>
          <h2 className="heading-md">Your privacy</h2>
        </div>
        <ul className="trust-list">
          <li>
            No account and no saved history. NIRNAY does not store the text or images you
            submit; they are processed for this request only.
          </li>
          <li>
            Obvious identifiers in text, such as email addresses, Indian phone numbers,
            PAN, and Aadhaar numbers, are redacted on the server before analysis.
          </li>
          <li>
            Images cannot be redacted before text recognition. Avoid uploading
            screenshots that contain sensitive details.
          </li>
          <li>
            With your consent, redacted text, extracted claims, and retrieved evidence are
            sent to external AI and search providers, under their own handling policies.
          </li>
        </ul>
      </article>

      <article className="trust-panel">
        <div className="trust-panel-head">
          <span aria-hidden="true" className="trust-icon">
            <Icon name="shield" size={20} />
          </span>
          <h2 className="heading-md">Responsible use</h2>
        </div>
        <ul className="trust-list">
          <li>
            NIRNAY is an information tool, not a financial adviser. It does not recommend
            investments, products, or actions, and it does not predict returns.
          </li>
          <li>
            Results can be incomplete or wrong. Confirm important claims with the original
            source or the relevant regulator before acting.
          </li>
          <li>
            “Unverified” means the evidence found did not establish a claim. It does not
            mean the claim is false.
          </li>
        </ul>
      </article>
    </section>
  );
}
