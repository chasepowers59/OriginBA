import { useId } from "react";

/**
 * Ori's mark: Origin's O, a ring from the accent into Origin teal with a spark in its gap --
 * an insight, and a hint of a speech bubble. Drawn from theme tokens, so it follows a
 * client's white-label accent and dark mode. `inverse` draws it in the current text colour,
 * for a filled button (a white plate lost the pale dark-mode ring). While Ori works the spark
 * travels the ring (still under reduced motion).
 */
export function OriMark({ size = "h-7 w-7", thinking = false, inverse = false }: {
  size?: string;
  thinking?: boolean;
  inverse?: boolean;
}) {
  const gradient = `ori-${useId().replace(/:/g, "")}`;
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={`shrink-0 ${size}`}>
      {inverse ? null : (
        <defs>
          <linearGradient id={gradient} x1="4" y1="4" x2="28" y2="28" gradientUnits="userSpaceOnUse">
            <stop offset="0" style={{ stopColor: "var(--accent-readable, var(--primary))" }} />
            <stop offset="1" style={{ stopColor: "var(--brand-teal-2)" }} />
          </linearGradient>
        </defs>
      )}
      {/* r 11: a 55-unit arc and a 14-unit gap centred at one-thirty (round caps close it to ~10) */}
      <circle cx="16" cy="16" r="11" fill="none" stroke={inverse ? "currentColor" : `url(#${gradient})`}
              strokeWidth="4" strokeLinecap="round" strokeDasharray="55 14.1" transform="rotate(-8 16 16)" />
      <g className={thinking ? "animate-spin motion-reduce:animate-none" : undefined}
         style={{ transformOrigin: "16px 16px", transformBox: "view-box", animationDuration: "1.6s" }}>
        <circle cx="23.78" cy="8.22" r="2.6" style={{ fill: inverse ? "currentColor" : "var(--brand-blue-1)" }} />
      </g>
    </svg>
  );
}
