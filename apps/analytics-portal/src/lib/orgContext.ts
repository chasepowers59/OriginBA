/** Whose data the reader is looking at. */

/** An admin looking at a client other than their own; an admin with no home org looking at any client. */
export function viewingAnotherClient(active: string | null | undefined, home: string | null | undefined): boolean {
  return Boolean(active) && active !== (home ?? "");
}
