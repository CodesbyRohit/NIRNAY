import type { Ref } from "react";
import { Button } from "@/components/ui/Button";
import { Icon, type IconName } from "@/components/ui/Icon";
import type { ApiErrorKind } from "@/lib/api";

const ERROR_COPY: Record<
  ApiErrorKind,
  { title: string; nextStep: string; retryable: boolean; icon: IconName }
> = {
  network: {
    title: "Couldn’t reach the analysis service",
    nextStep:
      "Check your internet connection and try again. If you run this service yourself, make sure the backend is running and the frontend’s API URL points to it.",
    retryable: true,
    icon: "wifiOff",
  },
  provider_unavailable: {
    title: "Analysis isn’t available right now",
    nextStep:
      "A required provider (AI model, search, or text recognition) is not configured or is temporarily unavailable. If you run this service, check the backend provider settings described in the README.",
    retryable: true,
    icon: "alert",
  },
  provider_failed: {
    title: "A provider returned an unusable response",
    nextStep:
      "To avoid showing unreliable results, nothing was displayed. This is often temporary, so try again.",
    retryable: true,
    icon: "alert",
  },
  malformed: {
    title: "The results could not be read",
    nextStep:
      "The service responded in an unexpected format, so nothing was displayed. Try again.",
    retryable: true,
    icon: "alert",
  },
  invalid_input: {
    title: "This input couldn’t be processed",
    nextStep: "Edit the content or choose a different image, then analyze again.",
    retryable: false,
    icon: "info",
  },
  too_large: {
    title: "This image is too large",
    nextStep: "Choose an image of 10 MiB or less, or crop it to the relevant part.",
    retryable: false,
    icon: "info",
  },
  unsupported_type: {
    title: "This file type isn’t supported",
    nextStep: "Choose a PNG, JPEG, or WebP screenshot.",
    retryable: false,
    icon: "info",
  },
  consent: {
    title: "Consent is required",
    nextStep: "Tick the consent box below to allow external processing, then analyze again.",
    retryable: false,
    icon: "info",
  },
  unknown: {
    title: "Analysis could not be completed",
    nextStep: "Try again in a moment.",
    retryable: true,
    icon: "alert",
  },
};

export function ErrorPanel({
  kind,
  message,
  onRetry,
  onDismiss,
  headingRef,
}: {
  kind: ApiErrorKind;
  message: string;
  onRetry: () => void;
  onDismiss: () => void;
  headingRef?: Ref<HTMLHeadingElement>;
}) {
  const copy = ERROR_COPY[kind];

  return (
    <section aria-labelledby="error-heading" className="error-panel" role="alert">
      <div className="error-panel-head">
        <Icon name={copy.icon} size={20} />
        <h2 className="heading-sm" id="error-heading" ref={headingRef} tabIndex={-1}>
          {copy.title}
        </h2>
      </div>
      <p className="body-copy">{message}</p>
      <p className="small-copy">{copy.nextStep}</p>
      <p className="small-copy">
        Your content is still on this page. No results were shown.
      </p>
      <div className="error-actions">
        {copy.retryable && (
          <Button onClick={onRetry} variant="secondary">
            <Icon name="refresh" size={16} />
            Try again
          </Button>
        )}
        <Button onClick={onDismiss} variant="link">
          Dismiss
        </Button>
      </div>
    </section>
  );
}
