# AI Usage Documentation

## LLM Provider
- **Model:** gemini-2.5-flash
- **Total LLM calls made:** 150 (1 call per transcript)
- **Estimated cost:** Within free tier
- **API provider:** Google AI Studio (aistudio.google.com)

## How the pipeline works
One LLM call per transcript. The prompt returns all fields in a single
JSON object — extraction, quality scores, last stage, next action, and
summary in one shot.

## AI Coding Tools Used
- **Claude (claude.ai):** Used for pipeline logic, prompt design,
  Flask routes, and HTML UI (~70% of code)
- **Google Colab:** Used to test and run the seed pipeline on all
  150 transcripts before deploying

## What I accepted from AI suggestions
- The single-prompt-per-transcript approach (cheaper and faster
  than chaining multiple calls)
- The Flask-based single-file architecture (simpler than
  FastAPI + separate frontend for this use case)
- Exponential backoff logic for Gemini rate limit handling

## What I rejected from AI suggestions
- Suggestion to use separate LLM calls per field group — rejected
  because it would cost 5x more tokens and add latency to the
  upload flow with minimal accuracy gain
- Suggestion to use a generic customer support prompt template —
  rejected because it used wrong field names (clarity, empathy)
  instead of the real estate specific fields required
  (discovery, pitch, objection_handling, next_step)

## Tamil-English handling
Gemini 2.5 Flash handles Tamil-English code-switching natively.
The prompt explicitly instructs the model to handle mixed language
transcripts, which is critical since all 150 calls contain Tamil
phrases like "vanakkam", "sollunga", "pesi mudichachu".
