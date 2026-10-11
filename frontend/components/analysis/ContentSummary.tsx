"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";

const PREVIEW_CHARS = 280;

export function ContentSummary({ label, text }: { label: string; text: string }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = text.length > PREVIEW_CHARS;
  const shown = expanded || !isLong ? text : `${text.slice(0, PREVIEW_CHARS).trimEnd()}…`;

  return (
    <section aria-labelledby="submitted-heading" className="aside-card">
      <h3 className="aside-title" id="submitted-heading">
        {label}
      </h3>
      <p className="submitted-text" id="submitted-text">
        {shown}
      </p>
      {isLong && (
        <Button
          aria-controls="submitted-text"
          aria-expanded={expanded}
          onClick={() => setExpanded((value) => !value)}
          variant="link"
        >
          {expanded ? "Show less" : "Show full text"}
        </Button>
      )}
      <p className="small-copy">
        Shown from this page’s memory. NIRNAY does not save submitted content.
      </p>
    </section>
  );
}
