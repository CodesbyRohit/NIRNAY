import type { ReactNode } from "react";
import { Icon, type IconName } from "@/components/ui/Icon";

export type Tone =
  | "supported"
  | "contradicted"
  | "needs"
  | "unverified"
  | "signal"
  | "demo"
  | "live"
  | "ai"
  | "neutral";

export function Badge({
  tone = "neutral",
  icon,
  size = "md",
  children,
}: {
  tone?: Tone;
  icon?: IconName;
  size?: "md" | "lg";
  children: ReactNode;
}) {
  return (
    <span className={`badge tone-${tone} ${size === "lg" ? "badge-lg" : ""}`}>
      {icon && <Icon name={icon} size={size === "lg" ? 18 : 14} />}
      {children}
    </span>
  );
}
