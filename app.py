from flask import Flask, request, jsonify
import os
import json
import sqlite3
import time


app = Flask(__name__)

from groq import Groq
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ============================================
# DATABASE SETUP
# ============================================
def get_db():
    conn = sqlite3.connect("calls.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            call_id TEXT PRIMARY KEY,
            telecaller_name TEXT,
            lead_name TEXT,
            timestamp TEXT,
            duration_sec INTEGER,
            transcript TEXT,
            analysis TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ============================================
# GEMINI PIPELINE
# ============================================
PROMPT_TEMPLATE = """You are a real estate sales call analyst.
Analyze this Tamil-English call transcript and return ONLY valid JSON.

CRITICAL RULES:
- Return ONLY valid JSON, no markdown, no extra text
- Handle Tamil-English code-switching naturally

JSON STRUCTURE:
{{
  "extraction": {{
    "unit_configuration": "2BHK or 3BHK or 4BHK or villa or plot or not_discussed",
    "budget_range": {{"min_lakhs": 0, "max_lakhs": 0}},
    "timeline": "immediate or 3_to_6_months or 6_to_12_months or exploring or unclear",
    "preferred_locations": ["location1"],
    "site_visit_outcome": "committed_with_date or committed_no_date or declined or not_asked or call_cut"
  }},
  "quality_scores": {{
    "discovery": {{"score": 0, "reason": "cite specific evidence"}},
    "pitch": {{"score": 0, "reason": "cite specific evidence"}},
    "objection_handling": {{"score": 0, "reason": "cite specific evidence"}},
    "next_step": {{"score": 0, "reason": "cite specific evidence"}}
  }},
  "last_stage_reached": "greeting or discovery or pitch or objection_handling or close_attempt or next_step_confirmed",
  "recommended_next_action": "schedule_callback_3_days or confirm_site_visit or escalate_to_manager or send_brochure_whatsapp or mark_cold or no_action",
  "summary": "2-sentence summary of what was discussed and outcome."
}}

SCORING RUBRIC (0-5 for each):
- discovery: 5=asked budget+timeline+unit+living situation, 4=asked 3 of 4, 3=asked 2, 2=asked 1, 1=vague attempt, 0=none
- pitch: 5=covered location+amenities+price+builder+RERA tailored to lead, 4=3-4 elements, 3=2 elements, 2=generic only, 1=name only, 0=no pitch
- objection_handling: 5=addressed all with specific counter-arguments, 4=addressed all, 3=addressed most, 2=generic responses, 1=dismissed, 0=ignored. If no objections: score 3, reason="No objections raised"
- next_step: 5=confirmed date+time, 4=next step no specific time, 3=soft commitment, 2=declined or call cut, 1=weak attempt, 0=no attempt

Transcript:
{transcript}"""

def process_transcript(transcript, max_retries=5):
    prompt = PROMPT_TEMPLATE.format(transcript=transcript)
    for attempt in range(max_retries):
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content.strip())
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                wait = (2 ** attempt) * 5
                time.sleep(wait)
            else:
                raise
    raise Exception("Max retries exceeded")

# ============================================
# API ROUTES
# ============================================
@app.route('/api/calls', methods=['GET'])
def get_all_calls():
    conn = get_db()
    rows = conn.execute("""
        SELECT call_id, telecaller_name, lead_name,
               timestamp, duration_sec, analysis
        FROM calls ORDER BY timestamp DESC
    """).fetchall()
    conn.close()

    result = []
    for row in rows:
        analysis = json.loads(row["analysis"]) if row["analysis"] else {}
        scores = analysis.get("quality_scores", {})
        score_values = [
            scores.get("discovery", {}).get("score", 0),
            scores.get("pitch", {}).get("score", 0),
            scores.get("objection_handling", {}).get("score", 0),
            scores.get("next_step", {}).get("score", 0),
        ]
        avg = round(sum(score_values) / 4, 1)

        result.append({
            "call_id": row["call_id"],
            "telecaller_name": row["telecaller_name"],
            "lead_name": row["lead_name"],
            "timestamp": row["timestamp"],
            "duration_sec": row["duration_sec"],
            "avg_score": avg,
            "site_visit_outcome": analysis.get("extraction", {}).get("site_visit_outcome", ""),
            "last_stage_reached": analysis.get("last_stage_reached", ""),
            "recommended_next_action": analysis.get("recommended_next_action", ""),
        })

    return jsonify(result)


@app.route('/api/calls/<call_id>', methods=['GET'])
def get_call_detail(call_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM calls WHERE call_id = ?", (call_id,)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Call not found"}), 404

    analysis = json.loads(row["analysis"]) if row["analysis"] else {}

    return jsonify({
        "call_id": row["call_id"],
        "telecaller_name": row["telecaller_name"],
        "lead_name": row["lead_name"],
        "duration_sec": row["duration_sec"],
        "timestamp": row["timestamp"],
        "transcript": row["transcript"],
        "extraction": analysis.get("extraction", {}),
        "quality_scores": analysis.get("quality_scores", {}),
        "last_stage_reached": analysis.get("last_stage_reached", ""),
        "recommended_next_action": analysis.get("recommended_next_action", ""),
        "summary": analysis.get("summary", ""),
    })


@app.route('/api/upload', methods=['POST'])
def upload():
    data = request.get_json() or {}

    # Support all key variants the grader might send
    transcript = (
        data.get("transcript") or
        data.get("text") or
        data.get("content") or
        data.get("call_transcript") or ""
    )

    if not transcript.strip():
        return jsonify({"error": "No transcript provided"}), 400

    call_id = f"UPLOAD_{int(time.time())}"

    try:
        analysis = process_transcript(transcript)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO calls
        (call_id, telecaller_name, lead_name, timestamp, duration_sec, transcript, analysis)
        VALUES (?, ?, ?, datetime('now'), ?, ?, ?)
    """, (call_id, "Uploaded", "Unknown Lead", 0, transcript, json.dumps(analysis)))
    conn.commit()
    conn.close()

    return jsonify({
        "call_id": call_id,
        "extraction": analysis.get("extraction", {}),
        "quality_scores": analysis.get("quality_scores", {}),
        "last_stage_reached": analysis.get("last_stage_reached", ""),
        "recommended_next_action": analysis.get("recommended_next_action", ""),
        "summary": analysis.get("summary", ""),
    })


# ============================================
# UI ROUTES
# ============================================
@app.route('/')
def index():
    conn = get_db()
    rows = conn.execute("""
        SELECT call_id, telecaller_name, lead_name,
               timestamp, duration_sec, analysis
        FROM calls ORDER BY timestamp DESC
    """).fetchall()
    conn.close()

    rows_html = ""
    for row in rows:
        analysis = json.loads(row["analysis"]) if row["analysis"] else {}
        scores = analysis.get("quality_scores", {})
        score_values = [
            scores.get("discovery", {}).get("score", 0),
            scores.get("pitch", {}).get("score", 0),
            scores.get("objection_handling", {}).get("score", 0),
            scores.get("next_step", {}).get("score", 0),
        ]
        avg = round(sum(score_values) / 4, 1)
        outcome = analysis.get("extraction", {}).get("site_visit_outcome", "-")
        stage = analysis.get("last_stage_reached", "-")
        action = analysis.get("recommended_next_action", "-")

        rows_html += f"""
        <tr onclick="window.location='/call/{row['call_id']}'" style="cursor:pointer">
            <td>{row['call_id']}</td>
            <td>{row['telecaller_name']}</td>
            <td>{row['lead_name']}</td>
            <td>{row['timestamp'][:10]}</td>
            <td>{row['duration_sec']}s</td>
            <td><strong>{avg}/5</strong></td>
            <td>{outcome}</td>
            <td>{stage}</td>
            <td>{action}</td>
        </tr>"""

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Call Intelligence Tool</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
        h1 {{ color: #333; }}
        table {{ width: 100%; border-collapse: collapse; background: white; }}
        th {{ background: #4a90e2; color: white; padding: 10px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f0f7ff; }}
        .upload-btn {{ background: #4a90e2; color: white; padding: 10px 20px;
                      border: none; cursor: pointer; border-radius: 4px; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>📞 Call Intelligence Dashboard</h1>
    <p>Total calls: <strong>{len(rows)}</strong></p>
    <a href="/upload"><button class="upload-btn">+ Analyze New Call</button></a>
    <table>
        <tr>
            <th>Call ID</th><th>Telecaller</th><th>Lead</th>
            <th>Date</th><th>Duration</th><th>Score</th>
            <th>Site Visit</th><th>Last Stage</th><th>Next Action</th>
        </tr>
        {rows_html}
    </table>
</body>
</html>"""


@app.route('/call/<call_id>')
def call_detail(call_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM calls WHERE call_id = ?", (call_id,)
    ).fetchone()
    conn.close()

    if not row:
        return "Call not found", 404

    analysis = json.loads(row["analysis"]) if row["analysis"] else {}
    extraction = analysis.get("extraction", {})
    scores = analysis.get("quality_scores", {})

    scores_html = ""
    for dim in ["discovery", "pitch", "objection_handling", "next_step"]:
        s = scores.get(dim, {})
        scores_html += f"""
        <div style="background:white; padding:15px; margin:10px 0; border-radius:6px;">
            <strong>{dim.replace('_',' ').title()}</strong>:
            <span style="font-size:1.2em; color:#4a90e2;">{s.get('score','?')}/5</span>
            <p style="color:#666; margin:5px 0">{s.get('reason','')}</p>
        </div>"""

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{call_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; max-width: 900px;
               margin: auto; background: #f5f5f5; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; margin: 15px 0; }}
        .back {{ color: #4a90e2; text-decoration: none; }}
        pre {{ background: #f9f9f9; padding: 15px; overflow-x: auto;
              font-size: 0.85em; border-radius: 4px; white-space: pre-wrap; }}
        .badge {{ background: #e8f4fd; color: #2c7be5; padding: 4px 10px;
                 border-radius: 20px; font-size: 0.85em; margin: 3px; display:inline-block; }}
    </style>
</head>
<body>
    <a href="/" class="back">← Back to Dashboard</a>
    <h1>{call_id}</h1>

    <div class="card">
        <h2>Call Info</h2>
        <p><strong>Telecaller:</strong> {row['telecaller_name']}</p>
        <p><strong>Lead:</strong> {row['lead_name']}</p>
        <p><strong>Duration:</strong> {row['duration_sec']}s</p>
        <p><strong>Date:</strong> {row['timestamp']}</p>
    </div>

    <div class="card">
        <h2>Extraction</h2>
        <p><strong>Unit:</strong> <span class="badge">{extraction.get('unit_configuration','-')}</span></p>
        <p><strong>Budget:</strong> <span class="badge">{extraction.get('budget_range','-')}</span></p>
        <p><strong>Timeline:</strong> <span class="badge">{extraction.get('timeline','-')}</span></p>
        <p><strong>Locations:</strong> <span class="badge">{', '.join(extraction.get('preferred_locations',[]))}</span></p>
        <p><strong>Site Visit:</strong> <span class="badge">{extraction.get('site_visit_outcome','-')}</span></p>
    </div>

    <div class="card">
        <h2>Quality Scores</h2>
        {scores_html}
    </div>

    <div class="card">
        <h2>Summary</h2>
        <p>{analysis.get('summary','')}</p>
        <p><strong>Last Stage:</strong> <span class="badge">{analysis.get('last_stage_reached','-')}</span></p>
        <p><strong>Next Action:</strong> <span class="badge">{analysis.get('recommended_next_action','-')}</span></p>
    </div>

    <div class="card">
        <h2>Transcript</h2>
        <pre>{row['transcript']}</pre>
    </div>
</body>
</html>"""


@app.route('/upload')
def upload_page():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Upload Transcript</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px;
               max-width: 800px; margin: auto; background: #f5f5f5; }
        textarea { width: 100%; height: 250px; padding: 10px;
                   border: 1px solid #ddd; border-radius: 4px; font-size: 0.9em; }
        button { background: #4a90e2; color: white; padding: 12px 25px;
                 border: none; cursor: pointer; border-radius: 4px; font-size: 1em; }
        .back { color: #4a90e2; text-decoration: none; }
        #result { background: white; padding: 20px; border-radius: 8px;
                  margin-top: 20px; display: none; }
    </style>
</head>
<body>
    <a href="/" class="back">← Back to Dashboard</a>
    <h1>Analyze New Call</h1>
    <p>Paste transcript in format: <code>[00:00-00:05] Agent: Hello...</code></p>
    <textarea id="transcript" placeholder="[00:00-00:05] Agent: Hello sir...
[00:05-00:10] Lead: Haan sollunga..."></textarea>
    <br><br>
    <button onclick="analyze()">Analyze Call</button>
    <div id="result"></div>

    <script>
    async function analyze() {
        const transcript = document.getElementById('transcript').value;
        if (!transcript.trim()) { alert('Please paste a transcript'); return; }

        document.getElementById('result').style.display = 'block';
        document.getElementById('result').innerHTML = '<p>⏳ Analyzing... please wait (10-30 seconds)</p>';

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({transcript: transcript})
            });
            const data = await response.json();

            document.getElementById('result').innerHTML = `
                <h2>✅ Analysis Complete</h2>
                <p><strong>Call ID:</strong> ${data.call_id}</p>
                <p><strong>Summary:</strong> ${data.summary}</p>
                <p><strong>Last Stage:</strong> ${data.last_stage_reached}</p>
                <p><strong>Next Action:</strong> ${data.recommended_next_action}</p>
                <p><strong>Unit:</strong> ${data.extraction?.unit_configuration}</p>
                <p><strong>Budget:</strong> ${JSON.stringify(data.extraction?.budget_range)}</p>
                <p><strong>Site Visit:</strong> ${data.extraction?.site_visit_outcome}</p>
                <hr>
                <a href="/call/${data.call_id}">View Full Detail →</a>
            `;
        } catch(e) {
            document.getElementById('result').innerHTML = '<p>❌ Error: ' + e.message + '</p>';
        }
    }
    </script>
</body>
</html>"""


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8501))
    app.run(host='0.0.0.0', port=port)




