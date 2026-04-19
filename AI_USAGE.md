# AI Usage Documentation

## LLM Provider
- **Model:** llama-3.1-8b-instant (via Groq)
- **Total LLM calls made:** 150 (1 call per transcript)
- **Estimated cost:** Free (Groq free tier)
- **API provider:** Groq (console.groq.com)

## Why Groq instead of Gemini
Initially attempted with Gemini 2.5 Flash but hit daily quota limits
after processing only 1-2 calls. Switched to Groq's llama-3.1-8b-instant
which has more generous free tier limits and successfully processed
all 150 transcripts without quota issues.

## How the pipeline works
One LLM call per transcript. The prompt returns all fields in a single
JSON object — extraction, quality scores, last stage, next action, and
summary in one shot.

## AI Coding Tools Used
- **Claude (claude.ai):** Used for pipeline logic, prompt design,
  Flask routes, and HTML UI (~70% of code)
- **Google Colab:** Used to run the seed pipeline on all 150
  transcripts before deploying

## What I accepted from AI suggestions
- The single-prompt-per-transcript approach (cheaper and faster
  than chaining multiple calls)
- The Flask-based single-file architecture (simpler than
  FastAPI + separate frontend for this use case)
- Exponential backoff logic for rate limit handling

## What I rejected from AI suggestions
- Suggestion to use separate LLM calls per field group — rejected
  because it would cost 5x more tokens and add latency to the
  upload flow with minimal accuracy gain
- Suggestion to use a generic customer support prompt template —
  rejected because it used wrong field names (clarity, empathy)
  instead of the real estate specific fields required
  (discovery, pitch, objection_handling, next_step)
- Sticking with Gemini despite repeated quota failures — switched
  to Groq which was more reliable for bulk processing

## Tamil-English handling
Llama 3.1 via Groq handles Tamil-English code-switching well.
The prompt explicitly instructs the model to handle mixed language
transcripts, which is critical since all 150 calls contain Tamil
phrases like "vanakkam", "sollunga", "pesi mudichachu".

