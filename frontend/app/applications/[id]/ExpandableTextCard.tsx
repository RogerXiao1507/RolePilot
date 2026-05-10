"use client"

import { useState } from "react"

type ExpandableTextCardProps = {
  title: string
  text: string
  collapsedHeight?: number
}

export default function ExpandableTextCard({
  title,
  text,
  collapsedHeight = 260,
}: ExpandableTextCardProps) {
  const [expanded, setExpanded] = useState(false)

  const hasLongContent = text.length > 500

  return (
    <div>
      <h2 className="rp-section-title mb-3">{title}</h2>

      <div className="rounded-lg border border-[var(--border)] bg-white p-5">
        <div
          className={`overflow-hidden text-sm leading-7 text-[var(--foreground)] transition-[max-height] duration-300 ${
            expanded ? "" : "relative"
          }`}
          style={{
            maxHeight: expanded ? "none" : `${collapsedHeight}px`,
          }}
        >
          {text || "No content provided."}

          {!expanded && hasLongContent && (
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-white to-transparent" />
          )}
        </div>

        {hasLongContent && (
          <button
            onClick={() => setExpanded((prev) => !prev)}
            className="rp-button-secondary mt-4"
          >
            {expanded ? "Show Less" : "Show More"}
          </button>
        )}
      </div>
    </div>
  )
}
