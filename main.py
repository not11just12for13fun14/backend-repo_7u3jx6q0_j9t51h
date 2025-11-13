import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

app = FastAPI(title="EchoLearn API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Lesson(BaseModel):
    id: str
    title: str
    description: str
    level: str = Field(default="beginner")
    topics: List[str] = Field(default_factory=list)


class InterpretRequest(BaseModel):
    user_id: Optional[str] = None
    transcript: str
    context: Optional[Dict[str, Any]] = None


class InterpretResponse(BaseModel):
    ai_response: str
    intent: str
    confidence: float = 0.7
    metadata: Dict[str, Any] = Field(default_factory=dict)


@app.get("/")
def read_root():
    return {"message": "EchoLearn Backend Running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from EchoLearn backend!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


@app.get("/api/lessons", response_model=List[Lesson])
def list_lessons():
    """Return a starter set of lessons. Later this can be moved to DB."""
    lessons = [
        Lesson(
            id="voice-basics",
            title="Voice Control Basics",
            description="Learn to navigate EchoLearn using your voice.",
            level="beginner",
            topics=["speech-to-text", "commands", "accessibility"],
        ),
        Lesson(
            id="math-fundamentals",
            title="Math Fundamentals",
            description="Practice arithmetic hands-free with guided prompts.",
            level="beginner",
            topics=["numbers", "addition", "subtraction"],
        ),
        Lesson(
            id="science-reading",
            title="Science Reading Comprehension",
            description="Listen to short passages and answer questions by voice.",
            level="intermediate",
            topics=["comprehension", "listening"],
        ),
    ]
    return lessons


@app.post("/api/interpret", response_model=InterpretResponse)
def interpret(req: InterpretRequest):
    """Very lightweight intent + response stub to enable the MVP.
    - Stores the interaction in the database if available
    - Returns an AI-like response using simple rules
    """
    transcript = (req.transcript or "").strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript is required")

    intent = "general.query"
    response_text = "I heard you. How can I assist with your learning today?"

    lower = transcript.lower()
    if any(w in lower for w in ["start", "begin", "go"]):
        intent = "session.start"
        response_text = "Starting your learning session. Which lesson would you like? Say 'list lessons' to hear options."
    elif "list" in lower and "lesson" in lower:
        intent = "lesson.list"
        response_text = "The lessons available are: Voice Control Basics, Math Fundamentals, and Science Reading Comprehension."
    elif any(w in lower for w in ["math", "add", "subtract", "plus", "minus"]):
        intent = "lesson.math"
        response_text = "Let's practice math. What is three plus five?"
    elif any(w in lower for w in ["stop", "end", "pause"]):
        intent = "session.stop"
        response_text = "Okay, pausing. Say 'resume' when you're ready."
    elif any(w in lower for w in ["hello", "hi", "hey"]):
        intent = "greeting"
        response_text = "Hello! I'm Echo, your hands-free tutor. How can I help?"

    # Try to persist interaction
    try:
        from database import create_document
        doc = {
            "user_id": req.user_id,
            "transcript": transcript,
            "intent": intent,
            "ai_response": response_text,
            "context": req.context or {},
            "created_at": datetime.now(timezone.utc),
        }
        create_document("interaction", doc)
    except Exception:
        # Database may be unavailable in some environments; ignore for MVP
        pass

    return InterpretResponse(ai_response=response_text, intent=intent, confidence=0.72, metadata={})


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
