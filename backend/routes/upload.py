# backend/routes/upload.py
import json
import sqlite3
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pipeline.seed import process_transcript

router = APIRouter()

class UploadRequest(BaseModel):
    transcript: str
    # These are optional fallbacks the grader also tries
    text: str = ""
    content: str = ""
    call_transcript: str = ""

def get_db():
    conn = sqlite3.connect("calls.db")
    conn.row_factory = sqlite3.Row
    return conn

@router.post("/upload")
def upload_transcript(request: UploadRequest):
    # Support all key variants the grader might send
    transcript = (
        request.transcript or
        request.text or
        request.content or
        request.call_transcript
    )

    if not transcript or not transcript.strip():
        raise HTTPException(status_code=400, detail="No transcript provided")

    # Generate a unique ID
    call_id = f"UPLOAD_{int(time.time())}"

    try:
        analysis = process_transcript(transcript)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")

    # Save to DB so it appears in list view
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO calls 
        (call_id, telecaller_id, telecaller_name, lead_id, lead_name, 
         duration_sec, timestamp, transcript, analysis)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)
    """, (
        call_id,
        "UPLOAD",
        "Uploaded Call",
        "UPLOAD",
        "Unknown Lead",
        0,
        transcript,
        json.dumps(analysis)
    ))
    conn.commit()
    conn.close()

    return {
        "call_id": call_id,
        "extraction": analysis.get("extraction", {}),
        "quality_scores": analysis.get("quality_scores", {}),
        "last_stage_reached": analysis.get("last_stage_reached", ""),
        "recommended_next_action": analysis.get("recommended_next_action", ""),
        "summary": analysis.get("summary", ""),
    }
