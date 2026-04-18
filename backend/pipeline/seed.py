# SIMPLIFIED FOR GOOGLE COLAB - NO FILE UPLOAD NEEDED
import json
import time
import re
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================
LLM_PROVIDER = "mock"  # Use "mock" - no API key needed
DB_PATH = "call_analysis.db"
model = genai.GenerativeModel("gemini-2.5-flash")

# ============================================
# PROMPT TEMPLATE (same as before)
# ============================================
SYSTEM_PROMPT = """You are a call analyst for a customer support team.
Given the transcript below, return ONLY a valid JSON object with these exact keys.

CRITICAL RULES:
- Return ONLY valid JSON, no other text
- Scores are 0-100 (0=worst, 100=best)
- For last_stage_reached: one of "greeting", "probing", "resolution", "closing", "abandoned"
- For recommended_next_action: one of "escalate", "follow_up", "close_success", "retrain_agent", "no_action"

JSON STRUCTURE:
{
  "extraction": {
    "unit_configuration": ...,   # ✅ From the assignment
    "budget_range": ...,         # ✅ From the assignment
    "timeline": ...,             # ✅ From the assignment
    "preferred_locations": ...,  # ✅ From the assignment
    "site_visit_outcome": ...    # ✅ From the assignment
}

"quality_scores": {
    "discovery": ...,            # ✅ From the assignment
    "pitch": ...,                # ✅ From the assignment
    "objection_handling": ...,   # ✅ From the assignment
    "next_step": ...             # ✅ From the assignment
}
  },
  "last_stage_reached": "",
  "recommended_next_action": "",
  "two_sentence_summary": ""
}"""

def build_user_prompt(transcript: str) -> str:
    return f"Transcript:\n\"\"\"\n{transcript}\n\"\"\""

# ============================================
# MOCK LLM (no API needed)
# ============================================
import json

import time
from google.api_core.exceptions import ResourceExhausted  # or just catch Exception

def real_llm_response(transcript, max_retries=5):
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        generation_config={
            "temperature": 0.2,
            "response_mime_type": "application/json",
        }
    )

    prompt = f"""[Your analysis prompt here...]
Transcript:
{transcript}
Return ONLY clean JSON. No extra text."""

    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text

        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "ResourceExhausted" in str(type(e)):
                wait_time = (2 ** attempt) * 10 + 5   # exponential backoff: 15s, 25s, 45s...
                print(f"  Rate limit hit (attempt {attempt+1}). Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                raise  # other real error

    raise Exception("Max retries exceeded due to rate limits")

# ============================================
# SIMPLIFIED PROCESSING
# ============================================
def create_mock_transcripts(count=150):
    """Create fake transcripts for testing"""
    transcripts = []
    for i in range(count):
        if i % 10 == 0:
            transcript = "Hello? Hello? *click*"  # Very short call
        elif i % 7 == 0:
            transcript = "Tamil conversation: நமஸ்காரம், எனக்கு ஒரு பிரச்சனை உள்ளது. I have a problem with my billing."
        else:
            transcript = f"Agent: Thank you for calling support. Customer: I need a refund for product {i}. Agent: Let me check. Customer: Thank you. Agent: Refund processed."

        transcripts.append({
            "id": f"call_{i+1:03d}",
            "transcript": transcript
        })
    return transcripts

import json
import time

def process_batch(transcripts):
    """Process all transcripts with caching + robust error handling"""
    results = []
    cache = {}  # Simple in-memory cache

    print(f"\n{'='*70}")
    print(f"Processing {len(transcripts)} transcripts in Colab")
    print(f"{'='*70}\n")

    for idx, call in enumerate(transcripts, 1):
        call_id = call["id"]
        transcript = call["transcript"]

        # Check cache
        if call_id in cache:
            print(f"[{idx}/{len(transcripts)}] {call_id} → cached")
            results.append(cache[call_id])
            continue

        # Process
        print(f"[{idx}/{len(transcripts)}] {call_id} → analyzing...", end=" ")

        # Debug transcript (helps see if input is too long or problematic)
        print("\n--- DEBUG TRANSCRIPT ---")
        print(f"Length: {len(transcript)} characters")
        print(transcript[:300] + "..." if len(transcript) > 300 else transcript)
        print("--- DEBUG TRANSCRIPT END ---\n")

        try:
            # Call your LLM wrapper
            raw_response = real_llm_response(transcript)

            # === CRITICAL DEBUGGING ===
            print("Raw response received (first 300 chars):")
            print(repr(raw_response[:300]) if raw_response else "EMPTY RESPONSE!")
            print("-" * 50)

            if not raw_response or not raw_response.strip():
                raise ValueError("LLM returned empty response")

            # Clean common issues (markdown code blocks, extra text)
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned.split("```json", 1)[1]
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```", 1)[1]
            if "```" in cleaned:
                cleaned = cleaned.split("```")[0]
            cleaned = cleaned.strip()

            # Parse JSON
            result = json.loads(cleaned)

            cache[call_id] = result
            results.append(result)
            print("✓ Success")

        except json.JSONDecodeError as e:
            print(f"✗ JSON Decode Error: {e}")
            print(f"Problematic response was: {repr(raw_response[:500])}")
            # Fallback: store error info instead of crashing
            error_result = {"error": "json_decode_failed", "raw_response": raw_response[:1000]}
            cache[call_id] = error_result
            results.append(error_result)

        except Exception as e:
            print(f"✗ Error: {type(e).__name__} - {e}")
            error_result = {"error": str(type(e).__name__), "message": str(e)}
            cache[call_id] = error_result
            results.append(error_result)

        # Small delay to avoid rate limits + show progress nicely
        time.sleep(0.2)   # You can reduce to 0.05 if needed

    print(f"\nBatch processing completed! Processed {len(results)} transcripts.\n")
    return results, cache

def analyze_results(results):
    """Print summary statistics"""
    stages = {}
    actions = {}
    fallbacks = 0

    for r in results:
        stage = r.get("last_stage_reached", "unknown")
        stages[stage] = stages.get(stage, 0) + 1

        action = r.get("recommended_next_action", "unknown")
        actions[action] = actions.get(action, 0) + 1

        if stage == "error" or action == "manual_review":
            fallbacks += 1

    print(f"\n{'='*60}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"\n📊 Last Stage Reached:")
    for stage, count in sorted(stages.items()):
        print(f"   {stage}: {count} calls ({count/len(results)*100:.1f}%)")

    print(f"\n🎯 Recommended Actions:")
    for action, count in sorted(actions.items()):
        print(f"   {action}: {count} calls ({count/len(results)*100:.1f}%)")

    print(f"\n⚠️  Fallbacks used: {fallbacks} ({fallbacks/len(results)*100:.1f}%)")

    # Show sample results
    print(f"\n📝 Sample Result (first call):")
    sample = results[0]
    print(f"   Summary: {sample['two_sentence_summary'][:80]}...")

    print(f"   Next Action: {sample['recommended_next_action']}")

# ============================================
# EXPORT RESULTS
# ============================================
def export_to_json(results, transcripts):
    """Export results as JSON for download"""
    export_data = []
    for i, result in enumerate(results):
        export_data.append({
            "call_id": transcripts[i]["id"],
            "transcript": transcripts[i]["transcript"],
            "analysis": result
        })

    # Save to file in Colab
    with open("analysis_results.json", "w") as f:
        json.dump(export_data, f, indent=2)

    print(f"\n✓ Results exported to 'analysis_results.json'")

    # In Colab, you can download it
    from google.colab import files
    files.download("analysis_results.json")
    print("✓ File downloaded to your computer")

# ============================================
# MAIN - RUN THIS IN COLAB
# ============================================
print("🚀 Call Transcript Analysis Pipeline - COLAB VERSION")
print("="*40)

# Create mock transcripts (change 150 to 10 for quick test)
print("\n📞 Creating mock transcripts...")
transcripts = create_mock_transcripts(150)  # Change to 10 for quick test
print(f"✓ Created {len(transcripts)} transcripts")

# Show example
print(f"\n📋 Example transcript #1:")
print(f"   ID: {transcripts[0]['id']}")
print(f"   Text: {transcripts[0]['transcript'][:100]}...")

# Process
print(f"\n⚙️  Starting batch processing...")
results, cache = process_batch(transcripts)

# Analyze
analyze_results(results)

# Export
export_to_json(results, transcripts)

print(f"\n✅ Done! Results saved and downloaded.")
print(f"   Total calls: {len(results)}")
print(f"   Unique calls in cache: {len(cache)}")
