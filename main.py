import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Child, Progress, Lesson, Game, Mission, Achievement, Recommendation

app = FastAPI(title="Gamified Digital Literacy API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Digital Literacy Backend Running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
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
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

# Seed minimal content if empty
@app.post("/seed")
def seed_content():
    if db is None:
        raise HTTPException(500, "Database not configured")

    def ensure(coll, doc):
        if db[coll].count_documents({}) == 0:
            create_document(coll, doc)

    ensure("lesson", Lesson(title="Understanding Devices", topic="devices", level="easy", description="Identify phone, tablet, computer").model_dump())
    ensure("lesson", Lesson(title="Safe vs Unsafe", topic="safety", level="easy", description="Spot safe online choices").model_dump())

    ensure("game", Game(title="Spot the Safe Choice", key="safe-choice", description="Tap the safe option").model_dump())

    ensure("mission", Mission(title="Warm-up Day", description="Finish 2 lessons today", target_type="lessons", target_count=2, reward="stars", reward_value=5).model_dump())

    return {"status": "ok"}

# Auth-lite child creation (no real auth for demo)
class ChildCreate(BaseModel):
    name: str
    age: int
    avatar: Optional[str] = None
    mode: Optional[str] = "child"

@app.post("/children")
def create_child(payload: ChildCreate):
    child = Child(**payload.model_dump())
    child_id = create_document("child", child)
    return {"id": child_id, "child": child}

@app.get("/children")
def list_children():
    docs = get_documents("child")
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs

# Progress tracking
class ProgressCreate(BaseModel):
    child_id: str
    item_type: str
    item_id: str
    score: int

@app.post("/progress")
def add_progress(payload: ProgressCreate):
    prog = Progress(child_id=payload.child_id, item_type=payload.item_type, item_id=payload.item_id, score=payload.score,
                    stars_earned=min(3, max(0, payload.score // 34)), points_earned=max(0, payload.score))
    prog_id = create_document("progress", prog)
    # Update child points/level basic
    try:
        cid = ObjectId(payload.child_id)
        child = db["child"].find_one({"_id": cid})
        if child:
            new_points = (child.get("points", 0) + prog.points_earned)
            new_level = 1 + new_points // 200
            db["child"].update_one({"_id": cid}, {"$set": {"points": new_points, "level": new_level}})
    except Exception:
        pass
    return {"id": prog_id}

# Simple Decision Tree-like recommendation
@app.get("/recommendations/{child_id}")
def get_recommendation(child_id: str):
    if db is None:
        raise HTTPException(500, "Database not configured")

    # Fetch child and last progress
    try:
        cid = ObjectId(child_id)
    except Exception:
        raise HTTPException(400, "Invalid child id")

    child = db["child"].find_one({"_id": cid})
    if not child:
        raise HTTPException(404, "Child not found")

    last = db["progress"].find({"child_id": child_id}).sort("completed_at", -1).limit(3)
    scores = [p.get("score", 0) for p in last]
    avg = sum(scores) / len(scores) if scores else 0

    # Decision Tree (hand-crafted rules for demo):
    # If average < 50 -> recommend easy safety lesson
    # If 50-80 -> medium etiquette or devices
    # If >80 -> advanced cybersecurity or a game
    if avg < 50:
        doc = db["lesson"].find_one({"level": "easy", "topic": "safety"}) or db["lesson"].find_one({"level": "easy"})
        if doc:
            return Recommendation(child_id=child_id, recommended_type="lesson", ref_id=str(doc["_id"]), title=doc.get("title"), reason="Average score low; reinforce safety basics").model_dump()
    elif avg <= 80:
        doc = db["lesson"].find_one({"level": "medium"}) or db["lesson"].find_one({"level": "easy"})
        if doc:
            return Recommendation(child_id=child_id, recommended_type="lesson", ref_id=str(doc["_id"]), title=doc.get("title"), reason="Doing well; try a medium challenge").model_dump()
    else:
        doc = db["game"].find_one({})
        if doc:
            return Recommendation(child_id=child_id, recommended_type="game", ref_id=str(doc["_id"]), title=doc.get("title"), reason="Great scores; keep it fun with a game").model_dump()

    # Fallback to a mission
    doc = db["mission"].find_one({})
    if doc:
        return Recommendation(child_id=child_id, recommended_type="mission", ref_id=str(doc["_id"]), title=doc.get("title"), reason="General growth mission").model_dump()

    return {"message": "No recommendation available yet"}

# Public content endpoints
@app.get("/lessons")
def list_lessons():
    docs = get_documents("lesson")
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs

@app.get("/games")
def list_games():
    docs = get_documents("game")
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs

@app.get("/missions")
def list_missions():
    docs = get_documents("mission")
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
