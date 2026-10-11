import { Icon, type IconName } from "@/components/ui/Icon";

// Each step mirrors the backend pipeline in backend/app/services/complete_analysis.py.
const STEPS: { icon: IconName; title: string; body: string }[] = [
  {
    icon: "split",
    title: "Separate the claims",
    body: "Obvious personal details are redacted on the server first. An AI model then splits the text into individual factual, financial, or promotional claims.",
  },
  {
    icon: "search",
    title: "Find sources",
    body: "Each claim is searched on its own. Up to three sources are ranked by source type, relevance, and date.",
  },
  {
    icon: "scale",
    title: "Assess against evidence",
    body: "An AI model compares each claim only with its retrieved sources and must cite them. Search snippets alone cannot support or contradict a claim.",
  },
  {
    icon: "rule",
    title: "Flag pressure language",
    body: "Fixed rules highlight wording such as guaranteed returns or urgency. These are warning signs, not proof of fraud.",
  },
];

export function HowItWorks() {
  return (
    <section aria-labelledby="how-heading" className="how-section">
      <div className="section-intro">
        <p className="eyebrow">How it works</p>
        <h2 className="heading-lg" id="how-heading">
          How NIRNAY checks content
        </h2>
      </div>
      <ol className="how-steps">
        {STEPS.map((step, index) => (
          <li className="how-step" key={step.title}>
            <div className="how-step-head">
              <span aria-hidden="true" className="how-step-icon">
                <Icon name={step.icon} size={20} />
              </span>
              <span className="how-step-number">Step {index + 1}</span>
            </div>
            <h3 className="heading-sm">{step.title}</h3>
            <p className="small-copy">{step.body}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
