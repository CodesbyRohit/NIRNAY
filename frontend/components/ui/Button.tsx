import type { ButtonHTMLAttributes } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "link";
  size?: "md" | "lg";
};

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  const variantClass = variant === "link" ? "link-button" : `btn btn-${variant}`;
  const sizeClass = size === "lg" && variant !== "link" ? "btn-lg" : "";
  return (
    <button
      className={`${variantClass} ${sizeClass} ${className}`.trim()}
      type={type}
      {...props}
    />
  );
}
