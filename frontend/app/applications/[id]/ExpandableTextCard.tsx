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
      <h2 className="mb-3 text-2xl font-semibold text-white">{title}</h2>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5">
        <div
          className={`overflow-hidden text-base leading-8 text-zinc-200 transition-all duration-300 ${
            expanded ? "" : "relative"
          }`}
          style={{
            maxHeight: expanded ? "none" : `${collapsedHeight}px`,
          }}
        >
          {text || "No content provided."}

          {!expanded && hasLongContent && (
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-zinc-900/95 to-transparent" />
          )}
        </div>

        {hasLongContent && (
          <button
            onClick={() => setExpanded((prev) => !prev)}
            className="mt-4 rounded-xl border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm font-medium text-zinc-200 transition hover:border-zinc-600 hover:bg-zinc-800"
          >
            {expanded ? "Show Less" : "Show More"}
          </button>
        )}
      </div>
    </div>
  )
}