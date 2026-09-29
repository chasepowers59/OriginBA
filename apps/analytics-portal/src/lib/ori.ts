/**
 * Ori: the intelligence inside Origin BA. Every Ori surface takes its words from here, so the
 * assistant, and later Ori's insights, summaries and anomaly notes, speak with one voice:
 * "Ori" as a name (never "the assistant"), present tense, plain words.
 */
export const ORI = {
  name: "Ori",
  ask: "Ask Ori",
  tagline: "Your AI analytics assistant",
  intro:
    "Ori reads your organization's reporting data, runs read-only queries and shows you every query it ran. It never sees another organization's data.",
  thinking: "Ori is analyzing your data…",
  followUp: "Ask Ori a follow-up…",
  firstQuestion: "How much was billed by cycle in the last 90 days?",
  askInstead: "Ask Ori instead",
  cannotAnswer: "Ori could not answer.",
  notConfigured:
    "Ori is not set up for this deployment yet (no model key). The governed metrics below still answer everyday questions.",
  worthInvestigating: "Ori found something worth investigating",
  askWhy: "Ask Ori why",
  read: "Ori's read",
  heading: "Where it's heading",
  actual: "Actual",
  projection: "Projection",
  likelyRange: (low: string, high: string) => `Likely ${low} to ${high}`,
  forecastChart: (label: string) => `${label} by month: actual, then projected`,
  askAbout: "Ask Ori about this",
  projectionNote: "A projection from past months, not a promise.",
} as const;
