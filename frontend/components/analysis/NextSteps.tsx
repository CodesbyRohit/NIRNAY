import { Icon } from "@/components/ui/Icon";

export function NextSteps({ steps, id }: { steps: string[]; id: string }) {
  if (steps.length === 0) return null;
  return (
    <section aria-labelledby={`${id}-next`} className="next-steps">
      <div className="block-head">
        <h4 className="heading-sm next-steps-heading" id={`${id}-next`}>
          <Icon name="compass" size={16} />
          What to check next
        </h4>
        <span className="tag">General verification steps</span>
      </div>
      <ol className="next-steps-list">
        {steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
    </section>
  );
}
