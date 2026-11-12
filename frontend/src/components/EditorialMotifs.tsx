import React from "react";

/**
 * Minimal editorial SVG motif representing women's & children's safety,
 * balanced justice, and breaking silence — strictly abstract and non-graphic.
 */
export const EditorialHeroArtwork: React.FC<{ className?: string }> = ({
  className = "",
}) => (
  <svg
    viewBox="0 0 240 170"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
    className={className}
  >
    {/* Subtle broken-silence acoustic arcs */}
    <path
      d="M36 85C36 42 70 10 112 10"
      stroke="#B91C1C"
      strokeWidth="1.25"
      strokeOpacity="0.28"
      strokeDasharray="4 4"
    />
    <path
      d="M22 85C22 35 62 -4 112 -4"
      stroke="#141414"
      strokeWidth="1"
      strokeOpacity="0.14"
    />
    <path
      d="M204 85C204 128 170 160 128 160"
      stroke="#B91C1C"
      strokeWidth="1.25"
      strokeOpacity="0.28"
      strokeDasharray="4 4"
    />

    {/* Protective shield frame */}
    <path
      d="M120 18L172 36V82C172 117 149 144 120 156C91 144 68 117 68 82V36L120 18Z"
      fill="#FFFFFF"
      stroke="#141414"
      strokeWidth="1.5"
    />
    <path
      d="M120 25L165 40.5V82C165 112 145.5 135.5 120 146.5C94.5 135.5 75 112 75 82V40.5L120 25Z"
      stroke="#B91C1C"
      strokeWidth="1"
      strokeOpacity="0.35"
    />

    {/* Symbolic justice scale beam at top of shield */}
    <line x1="94" y1="50" x2="146" y2="50" stroke="#141414" strokeWidth="1.4" />
    <line x1="120" y1="42" x2="120" y2="54" stroke="#B91C1C" strokeWidth="1.6" />
    <circle cx="94" cy="50" r="2.2" fill="#B91C1C" />
    <circle cx="146" cy="50" r="2.2" fill="#B91C1C" />
    <path d="M88 60H100L94 50L88 60Z" stroke="#141414" strokeWidth="1" fill="#FAFAF8" />
    <path d="M140 60H152L146 50L140 60Z" stroke="#141414" strokeWidth="1" fill="#FAFAF8" />

    {/* Abstract dignified woman silhouette (charcoal) */}
    <circle cx="110" cy="76" r="6.5" fill="#141414" />
    <path
      d="M97 124L103 91C103.8 87 106.8 85 110 85C113.2 85 116.2 87 117 91L123 124H97Z"
      fill="#141414"
    />

    {/* Abstract child silhouette alongside (crimson) */}
    <circle cx="133" cy="91" r="5" fill="#B91C1C" />
    <path
      d="M124 124L128 102C128.6 99 130.6 97.5 133 97.5C135.4 97.5 137.4 99 138 102L142 124H124Z"
      fill="#B91C1C"
    />

    {/* Grounding baseline */}
    <line x1="88" y1="124" x2="152" y2="124" stroke="#141414" strokeWidth="1.4" />
  </svg>
);

export const JusticeScaleIcon: React.FC<{ className?: string }> = ({
  className = "h-4 w-4",
}) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.75"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
    className={className}
  >
    <path d="M12 3v18" />
    <path d="M5 7h14" />
    <path d="M3 14l2-7 2 7a2 2 0 0 1-4 0Z" />
    <path d="M17 14l2-7 2 7a2 2 0 0 1-4 0Z" />
    <path d="M8 21h8" />
  </svg>
);

