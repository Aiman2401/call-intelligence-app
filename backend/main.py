# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.calls import router as calls_router
from routes.upload import router as upload_router

app = FastAPI(title="Call Intelligence Tool")

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(calls_router, prefix="/api")
app.include_router(upload_router, prefix="/api")

@app.get("/")
def root():
    return {"status": "ok", "message": "Call Intelligence API is running"}
