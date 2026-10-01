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
  heading: "Forecasts",
  actual: "Actual",
  forecast: "Forecast",
  likelyRange: (low: string, high: string) => `Likely ${low} to ${high}`,
  forecastChart: (label: string) => `${label} by month: actual, then forecast`,
  askAbout: "Ask Ori about this",
  forecastNote: "A forecast from past months, not a promise.",
  seeAllForecasts: "See all forecasts →",
  forecastsIntro:
    "Where each Home card is likely to land over the next three months. Each forecast uses one of two methods: the same months last year, scaled by how the last three months compared with a year earlier, or the average of the last 12 months, whichever was more accurate on your own past months.",
  forecastsBar:
    "A forecast is shown only when, replayed on your past months, its three-month total was within 15% in a typical case and within 25% four times in five. The shaded band is that past accuracy.",
  forecastsThrough: (month: string) => `Built on complete months through ${month}.`,
  noForecasts:
    "No forecast is accurate enough to show yet. Each card needs at least two years of monthly history that a method could have predicted closely.",
} as const;
