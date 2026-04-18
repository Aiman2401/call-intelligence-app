# backend/routes/calls.py
import json
import sqlite3
from fastapi import APIRouter, HTTPException

router = APIRouter()

def get_db():
    conn = sqlite3.connect("calls.db")
    conn.row_factory = sqlite3.Row
    return conn

@router.get("/calls")
def get_all_calls():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            call_id, telecaller_name, lead_name,
            timestamp, duration_sec, analysis
        FROM calls
        ORDER BY timestamp DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        analysis = json.loads(row["analysis"]) if row["analysis"] else {}
        scores = analysis.get("quality_scores", {})

        # Calculate average score
        score_values = [
            scores.get("discovery", {}).get("score", 0),
            scores.get("pitch", {}).get("score", 0),
            scores.get("objection_handling", {}).get("score", 0),
            scores.get("next_step", {}).get("score", 0),
        ]
        avg_score = round(sum(score_values) / len(score_values), 1)

        result.append({
            "call_id": row["call_id"],
            "telecaller_name": row["telecaller_name"],
            "lead_name": row["lead_name"],
            "timestamp": row["timestamp"],
            "duration_sec": row["duration_sec"],
            "avg_score": avg_score,
            "site_visit_outcome": analysis.get("extraction", {}).get("site_visit_outcome", ""),
            "last_stage_reached": analysis.get("last_stage_reached", ""),
            "recommended_next_action": analysis.get("recommended_next_action", ""),
        })

    return result


@router.get("/calls/{call_id}")
def get_call_detail(call_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM calls WHERE call_id = ?", (call_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Call not found")

    analysis = json.loads(row["analysis"]) if row["analysis"] else {}

    return {
        "call_id": row["call_id"],
        "telecaller_id": row["telecaller_id"],
        "telecaller_name": row["telecaller_name"],
        "lead_id": row["lead_id"],
        "lead_name": row["lead_name"],
        "duration_sec": row["duration_sec"],
        "timestamp": row["timestamp"],
        "transcript": row["transcript"],
        "extraction": analysis.get("extraction", {}),
        "quality_scores": analysis.get("quality_scores", {}),
        "last_stage_reached": analysis.get("last_stage_reached", ""),
        "recommended_next_action": analysis.get("recommended_next_action", ""),
        "summary": analysis.get("summary", ""),
    }
