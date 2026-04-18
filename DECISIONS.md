# Call Intelligence Tool - Technical Decisions

## Scoring Rubric Decisions

These rubrics will be used in the Gemini prompt for scoring all 150 calls. Each dimension uses a 0-5 scale with specific behavioral anchors to ensure consistent scoring across different evaluators.

---

## 1. Discovery (0-5 scale)
**What it measures:** Did the telecaller ask about budget, timeline, unit preference (BHK/villa/plot), and current living situation?

| Score | Anchor Description |
|-------|-------------------|
| **5 – Excellent** | Asked about all 4 dimensions (budget, timeline, unit preference, current living situation) with meaningful follow-up probing |
| **4 – Good** | Asked about 3 of the 4 dimensions |
| **3 – Average** | Asked about 2 of the 4 dimensions |
| **2 – Below Average** | Asked about only 1 dimension, OR asked about 2-3 but only superficially (e.g., "what are you looking for?" with no follow-up) |
| **1 – Poor** | Vague discovery attempt only ("tell me what you need") with no specific questions |
| **0 – Unacceptable** | No discovery questions at all — went straight to pitch or greeting |

---

## 2. Pitch (0-5 scale)
**What it measures:** Did the telecaller explain the project's value proposition — location, amenities, pricing, builder credibility, USPs?

| Score | Anchor Description |
|-------|-------------------|
| **5 – Excellent** | Covered 4+ elements (location, amenities, pricing, builder credibility, RERA, possession timeline, USPs) with details tailored to lead's needs |
| **4 – Good** | Covered 3-4 elements clearly with specific details |
| **3 – Average** | Covered 2 elements adequately with some specifics |
| **2 – Below Average** | Covered only 1 element, OR mentioned 2-3 but only as generic statements ("good location, good amenities") without specifics |
| **1 – Poor** | Attempted pitch but only name-dropped project without any substantive details |
| **0 – Unacceptable** | No pitch delivered — call ended before any project explanation |

---

## 3. Objection Handling (0-5 scale)
**What it measures:** When the lead raised concerns (price, location, timing, competition), did the telecaller address them substantively?

| Score | Anchor Description |
|-------|-------------------|
| **5 – Excellent** | Addressed all objections with specific, relevant counter-arguments AND successfully moved conversation forward |
| **4 – Good** | Addressed all objections substantively (not dismissive), but may have been slightly repetitive or slow |
| **3 – Average** | Addressed most objections, but 1 objection was ignored or handled poorly (e.g., "no sir, that's not true" without explanation) |
| **2 – Below Average** | Acknowledged objections but gave generic/unconvincing responses ("it's a good area, trust me") |
| **1 – Poor** | Dismissed or argued with lead without addressing the actual concern ("you're wrong about that") |
| **0 – Unacceptable** | No objection handling attempted — ignored the concern and continued pitch |

**Special case:** If lead raised no objections, score as N/A and document in reason field.

---

## 4. Next Step (0-5 scale)
**What it measures:** Did the telecaller attempt to secure a concrete next action — site visit date, callback time, document sharing?

| Score | Anchor Description |
|-------|-------------------|
| **5 – Excellent** | Secured a confirmed next step with specific date/time (site visit scheduled, exact callback day and time agreed) |
| **4 – Good** | Secured a next step but without specific timing (e.g., "I'll share brochure," "call next week" without exact day) |
| **3 – Average** | Attempted to close but lead deferred vaguely ("I'll think about it," "I'll discuss with family") — telecaller still got a soft commitment |
| **2 – Below Average** | Attempted to close but lead clearly declined OR call cut before lead could respond |
| **1 – Poor** | Weak attempt ("we'll talk later") with no specificity or follow-through plan |
| **0 – Unacceptable** | No next step attempted — call ended without any closing effort |

---

## Alternatives Considered

Before finalizing this 0-5 rubric, I considered:

1. **3-point scale (1-3):** Rejected because 0-5 gives finer granularity for coaching telecallers. A score of 2 vs 3 matters for performance improvement plans.

2. **Binary pass/fail:** Rejected because sales performance has too much nuance. A telecaller who asked 3 of 4 discovery questions deserves different coaching than one who asked 0.

3. **Separate rubrics per call stage:** Rejected for MVP simplicity. Different call stages (discovery vs closing) naturally require different behaviors, but a unified rubric with clear per-dimension anchors works for now.

4. **Weighted dimensions:** Considered giving discovery higher weight for early-stage leads. Deferred to post-MVP iteration.

---

## Implementation Notes for Gemini Prompt

These rubrics will be included directly in the system prompt. The LLM must return for each dimension:
- `score`: integer 0-5
- `reason`: 1-2 sentence explanation **citing specific transcript evidence**

**Example reason format:**
> "Asked about budget (42L fit?) and unit preference (2BHK), but never probed timeline or current living situation. Lead volunteered timeline (6 months) unprompted."

**What I'd change with more time:**
- Validate rubric against 10 sample calls with a second human rater to check inter-rater reliability
- Add dimension weights based on call stage (discovery matters more for early calls)
- Create separate rubrics for different call types (cold vs warm leads)

---

## Other Key Technical Decisions

### Decision 1: One LLM Call per Transcript
**Why:** Minimizes latency for upload flow and reduces cost. Single JSON output contains extraction + scoring + stage + next-action + summary.

**Alternatives considered:** Separate calls per field group (extraction then scoring). Rejected because 2x latency and 2x cost for ~5% accuracy gain.

### Decision 2: Gemini Flash as LLM Provider
**Why:** Free tier supports 150 transcripts + upload testing. Good Tamil-English code-switching handling.

**Alternatives considered:** GPT-4 (better but costs money), Groq (faster but worse with Tamil). Gemini balances cost and quality.

### Decision 3: Pre-process All 150 Calls at Startup
**Why:** Dashboard loads instantly with all data. No waiting for LLM on page load.

**Alternatives considered:** On-demand processing. Rejected because manager would wait 2-3 seconds per call click.

### Decision 4: SQLite for Local Development
**Why:** Zero config, works in Colab, easy to migrate to PostgreSQL later.

**Alternatives considered:** Supabase (production-ready but adds complexity), JSON file (no querying). SQLite is the right balance.

### Decision 5: Upload Flow Uses Auto-generated ID
**Why:** User doesn't need to think about IDs. Format: `UPLOAD_YYYYMMDD_HHMMSS`

**Alternatives considered:** User-provided ID (more flexible but error-prone). Auto-generation is simpler for non-technical sales managers.
