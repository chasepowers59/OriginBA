# Analytics assistant: token budget

Every number here is MEASURED on Ellensburg 25.4 with `claude-sonnet-5`, 2026-09-15, from the
`usage` the API returns (and, since the same day, the `assistant_ask` audit row every question
writes: `input_tokens=..; output_tokens=..; cache_read_input_tokens=..; cache_creation_input_tokens=..;
turns=..; model=..; steps=..; question: ...`). Read spend per org or per person from that table;
there is no second ledger.

## What a question costs, and where the tokens go

Token classes bill differently: uncached input 1x, cache write 1.25x (2x with the 1h TTL), cache
read 0.1x, output ~5x. "Equivalent" below = tokens priced as uncached input.

| Question | turns | uncached in | cache write | cache read | output | ≈ input-equivalent |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| "Billed in the last 90 days by bill cycle" — first form (no message caching, notes inlined) | 4 | 19,240 | (not counted) | (not counted) | 1,114 | ≥ 28K |
| Same, moving cache breakpoint + 50-row model view | 3 | 6 | 10,270 | 76,969 | 1,283 | ≈ 20.5K |
| Same, reference notes behind `search_knowledge` (default now) | 3 | 6 | 14,172 | 16,734 | 1,295 | ≈ 19.4K, and the next question in the hour reads it all at 0.1x |
| Follow-up on the thread ("exclude the test cycle") | 2 | 4 | 1,836 | 46,816 | 440 | ≈ 7K |
| Arrears over 90 days by class + trust (5 tool calls) | 4 | 8 | 7,508 | 99,501 | 2,102 | ≈ 19.3K |

Where a turn's cache read went before the change: the system prompt + tools were ~22.7K tokens
(head ~3K, reference notes ~19.5K, tools ~1K), re-read on EVERY turn — ~68K of a 3-turn
question's 77K. The notes are now a tool the model calls when it needs them (it called
`search_knowledge` unprompted on the arrears question); the prefix is ~3.5K.

Rule of thumb after the changes: **a typical question is ~15–20K input-equivalent + ~1.3K
output; a follow-up ~7K + ~0.5K.** Output is the expensive class per token; the prompt already
asks for short answers and `MAX_TOKENS` caps a turn at 2,048.

## The levers, in the order they pay

| Lever | State | Effect measured / expected |
| --- | --- | --- |
| Moving cache breakpoint on the latest user turn (`_mark_prefix`) | ON | uncached input 19,240 → 6 per question |
| Reference notes behind `search_knowledge`, not inlined (`ASSISTANT_INLINE_KNOWLEDGE` off) | ON | cache reads 76,969 → 16,734 per question (−78%) |
| The model sees 50 rows of a result, the screen 200 (`MAX_ROWS_MODEL`) | ON | bounds the largest tool result; the model aggregates in SQL anyway |
| Thread stubs tool results on the way back (`_trim_thread`) | ON | a follow-up re-sends questions and answers, never rows |
| `ASSISTANT_CACHE_TTL=1h` | set in production | 5-minute cache expires between a real user's questions and is rewritten each time (14K × 1.25); the 1h write costs 14K × 2 once and every later question in the hour reads at 0.1x. Pays back from the second question. Leave unset for burst testing. |
| `MAX_TURNS=8`, `MAX_TOKENS=2048` | ON | a runaway question costs at most ~8 turns |
| Prompt asks for one well-aimed query, short answers | ON | 3 turns is the norm; the arrears question took 5 tool calls because it verified two canvases |

Not done, in order of likely value once there is real usage to measure against:

1. **Per-org daily budget** — sum `assistant_ask` rows for the org today, refuse with 429 past
   `ASSISTANT_DAILY_TOKEN_BUDGET`. Needs the audit query; a two-hour change.
2. **Per-person rate limit** (questions per minute) in the route.
3. **`describe_canvas` is the biggest tool result** (a 100-column canvas is ~4–5K tokens).
   Trim descriptions to one line, or return measures/dimensions/dates first and the rest on
   request. Measure on `rpt_bill_segment` before and after.
4. **Model routing**: Haiku 4.5 for "which canvas / what does X mean" questions, Sonnet for
   SQL. Only after a quality comparison on the fixed question set below — cheaper and wrong
   is worse than nothing.
5. **Answer length**: the model repeats the SQL in the answer text although the panel already
   shows it under the query card. One prompt line ("do not repeat the SQL; the reader sees it")
   saves ~200–400 output tokens per answer — the expensive class. Try it, then measure.

## Testing protocol (spend as little as possible)

- **Plumbing, UI, fences, integrity lines: `ASSISTANT_MODEL=stub`.** Free, no key, exercises
  the whole path including the database. The real model is for PROMPT and ANSWER QUALITY only.
- **A fixed question set, run once per prompt change**, not per code change:
  1. "How much was billed in the last 90 days, by bill cycle?" (one canvas, one aggregate)
  2. follow-up: "Exclude the test cycle. What is the total then?" (thread reuse)
  3. "How much is in arrears over 90 days, by customer class, and can I trust that number?"
     (search_knowledge + verification_status)
  Three questions ≈ 50K input-equivalent + 4K output. Read the `usage` line, not just the answer.
- Ask in bursts (inside the 5-minute cache window) when testing several things.
- Never loop the model in a test; `tests/test_assistant.py` uses a fake client.

## Quality notes from the first real conversations (for the prompt, not the budget)

- Oracle boolean: the model wrote `"Is Frozen" = TRUE` once and `= 1` afterwards; both ran.
- `SYSDATE - 90` vs `TRUNC(SYSDATE) - 90` moved the 90-day total from $1.40M to $1.74M —
  one bill-cycle day sits on the boundary. The answer stated its window each time, which is
  the right behaviour; a fixed convention (`TRUNC(SYSDATE) - 90`) belongs in the prompt.
- It flagged "TEST BILL CYCLE FOR RELEASE 26" carrying $462K unprompted, and read the
  integrity verdict correctly ("rows added since the build, not a logic error").
