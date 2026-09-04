/**
 * What this org's SQL workspace can actually reach.
 *
 * The page told everyone "Query the CISADM schema you know from CIS", which was
 * incomplete: both engines reach CISADM AND the reporting canvases beside it. Measured
 * against the running fence rather than assumed — a Postgres org's rejection message
 * names its own scope, "The workspace is scoped to cisadm, reporting", with staging and
 * core correctly refused as internal build layers.
 *
 * This is the architecture stated in one sentence: the app surfaces read the canvases,
 * and the SQL tab is where CISADM becomes reachable.
 */
export function workspaceScope(engine: string | undefined | null): string {
  const tail = "Start from a business question or browse the table guide.";
  switch (engine) {
    case "postgres":
      return (
        "Query CISADM, the schema you know from CIS, landed in this client's warehouse — " +
        `and the governed reporting canvases beside it. ${tail}`
      );
    case "oracle_dbt":
      return (
        "Query CISADM, the schema you know from CIS, and the governed reporting canvases " +
        `beside it in ORIGINBA_REPORTING. ${tail}`
      );
    case "oracle":
      return `Query the CISADM schema you know from CIS. ${tail}`;
    default:
      // Engine is learned on mount; promise no schema until it is known.
      return tail;
  }
}
