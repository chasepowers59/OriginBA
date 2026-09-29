/** Ori's mark: the Origin infinity mark in a soft brand circle, beside Ori's name wherever Ori speaks. */
export function OriMark({ size = "h-7 w-7" }: { size?: string }) {
  return (
    <span aria-hidden="true" className={`inline-flex shrink-0 items-center justify-center rounded-full bg-primary/10 ring-1 ring-primary/20 ${size}`}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/origin-mark.png" alt="" className="h-1/2 w-auto" />
    </span>
  );
}
