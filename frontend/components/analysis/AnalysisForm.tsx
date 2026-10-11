import type { FormEvent, RefObject } from "react";
import type { HealthState } from "@/components/analysis/SiteHeader";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

export type InputMode = "text" | "screenshot";

export const MAX_CONTENT_CHARS = 20_000;
export const DEMO_CONTENT =
  "SEBI approved XYZ investment plan. Guaranteed 30% return. Only 200 slots remaining. Join NOW!";

export function AnalysisForm({
  inputMode,
  onInputModeChange,
  content,
  onContentChange,
  screenshotFile,
  onScreenshotChange,
  screenshotInputRef,
  consent,
  onConsentChange,
  formError,
  isAnalyzing,
  health,
  onSubmit,
  onLoadExample,
}: {
  inputMode: InputMode;
  onInputModeChange: (mode: InputMode) => void;
  content: string;
  onContentChange: (value: string) => void;
  screenshotFile: File | null;
  onScreenshotChange: (file: File | null) => void;
  screenshotInputRef: RefObject<HTMLInputElement | null>;
  consent: boolean;
  onConsentChange: (value: boolean) => void;
  formError: string | null;
  isAnalyzing: boolean;
  health: HealthState;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onLoadExample: () => void;
}) {
  return (
    <section aria-labelledby="input-heading" className="card card-raised input-card">
      <div className="input-card-head">
        <h2 className="heading-md" id="input-heading">
          What would you like to check?
        </h2>
        <p className="small-copy">
          Paste a forwarded message, social post, advert, or a single claim.
        </p>
      </div>

      <form noValidate onSubmit={onSubmit}>
        <div aria-label="Choose input method" className="segmented" role="group">
          <button
            aria-pressed={inputMode === "text"}
            className="segmented-option"
            onClick={() => onInputModeChange("text")}
            type="button"
          >
            <Icon name="document" size={16} />
            Paste text
          </button>
          <button
            aria-pressed={inputMode === "screenshot"}
            className="segmented-option"
            onClick={() => onInputModeChange("screenshot")}
            type="button"
          >
            <Icon name="image" size={16} />
            Upload screenshot
          </button>
        </div>

        {inputMode === "text" ? (
          <div className="field">
            <label className="field-label" htmlFor="financial-content">
              Financial content to check
            </label>
            <textarea
              aria-describedby="content-help content-count"
              aria-invalid={formError !== null && !content.trim() ? true : undefined}
              className="content-input"
              id="financial-content"
              maxLength={MAX_CONTENT_CHARS}
              onChange={(event) => onContentChange(event.target.value)}
              placeholder="For example: “SEBI-approved plan. Guaranteed 3% monthly return. Only today!”"
              value={content}
            />
            <div className="field-meta">
              <p id="content-help">
                Remove personal account or contact details before pasting.
              </p>
              <p className="tabular-nums" id="content-count">
                {content.length.toLocaleString("en-IN")} /{" "}
                {MAX_CONTENT_CHARS.toLocaleString("en-IN")}
              </p>
            </div>
          </div>
        ) : (
          <div className="field">
            <label className="upload-drop" htmlFor="screenshot-file">
              <span aria-hidden="true" className="upload-icon">
                <Icon name="upload" size={22} />
              </span>
              <span className="upload-title">
                {screenshotFile ? "Choose a different screenshot" : "Choose a screenshot"}
              </span>
              <span className="small-copy" id="screenshot-help">
                PNG, JPEG, or WebP, up to 10 MiB. The image is processed for this request
                only and is not saved by NIRNAY.
              </span>
              <input
                accept="image/png,image/jpeg,image/webp"
                aria-describedby="screenshot-help"
                className="sr-only"
                id="screenshot-file"
                onChange={(event) => onScreenshotChange(event.target.files?.[0] ?? null)}
                ref={screenshotInputRef}
                type="file"
              />
            </label>
            {screenshotFile && (
              <div className="selected-file">
                <Icon name="image" size={16} />
                <span className="selected-file-name">{screenshotFile.name}</span>
                <span className="small-copy tabular-nums">
                  {(screenshotFile.size / (1024 * 1024)).toFixed(2)} MiB
                </span>
                <Button onClick={() => onScreenshotChange(null)} variant="link">
                  Remove
                </Button>
              </div>
            )}
          </div>
        )}

        <div className="example-row">
          <Button onClick={onLoadExample} variant="link">
            Load an illustrative example
          </Button>
          <p className="small-copy">
            Fictional demonstration only; “XYZ” is not a real investment product.
          </p>
        </div>

        <div className="consent-box">
          <label className="consent-row">
            <input
              checked={consent}
              className="consent-checkbox"
              onChange={(event) => onConsentChange(event.target.checked)}
              type="checkbox"
            />
            <span>
              <span className="consent-title">I consent to external processing</span>
              <span className="consent-detail">
                Redacted text is sent to an external AI provider for claim extraction, and
                extracted claims plus retrieved evidence are sent to external providers for
                source retrieval and assessment. If I upload a screenshot, the image is also
                sent to the configured text-recognition (OCR) provider.
              </span>
            </span>
          </label>
        </div>

        {health === "offline" && (
          <p className="inline-notice" role="status">
            <Icon name="wifiOff" size={16} />
            The analysis service is not responding right now. You can still try; if it
            fails, check that the backend is running.
          </p>
        )}

        {formError && (
          <p className="form-error" id="form-error" role="alert">
            <Icon name="alert" size={16} />
            {formError}
          </p>
        )}

        <div className="submit-row">
          <Button
            aria-busy={isAnalyzing}
            aria-describedby={formError ? "form-error" : undefined}
            disabled={isAnalyzing}
            size="lg"
            type="submit"
          >
            {isAnalyzing
              ? "Analyzing…"
              : inputMode === "screenshot"
                ? "Analyze screenshot"
                : "Analyze content"}
            {!isAnalyzing && <Icon name="arrowRight" size={18} />}
          </Button>
          <p className="small-copy">
            Informational only. NIRNAY does not give investment advice.
          </p>
        </div>
      </form>
    </section>
  );
}
