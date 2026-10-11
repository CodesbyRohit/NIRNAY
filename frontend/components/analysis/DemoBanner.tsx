import { Icon } from "@/components/ui/Icon";

export function DemoBanner() {
  return (
    <section aria-labelledby="demo-heading" className="demo-banner">
      <Icon name="flask" size={20} />
      <div>
        <h3 className="heading-sm" id="demo-heading">
          Illustrative demo evidence, not live research
        </h3>
        <p className="small-copy">
          Some or all sources below are fixed demonstration examples supplied by this
          service, not results from a live search. Do not rely on them to judge real
          content.
        </p>
      </div>
    </section>
  );
}
