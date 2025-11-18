"""
Database Schemas for Gamified Digital Literacy App (Ages 5–8)

Each Pydantic model represents a MongoDB collection. The collection name is the
lowercased class name (e.g., Child -> "child").
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# Core profiles
class Child(BaseModel):
    name: str = Field(..., description="Child's display name")
    age: int = Field(..., ge=3, le=10, description="Age in years")
    avatar: Optional[str] = Field(None, description="Avatar image URL or key")
    mode: Literal["child", "guest"] = Field("child", description="Access mode")
    points: int = Field(0, ge=0)
    level: int = Field(1, ge=1)
    stars: int = Field(0, ge=0)
    badges: List[str] = Field(default_factory=list)

class Parent(BaseModel):
    name: str
    email: str

class Teacher(BaseModel):
    name: str
    email: str
    school: Optional[str] = None

# Learning content
class Lesson(BaseModel):
    title: str
    topic: Literal[
        "devices",
        "safety",
        "etiquette",
        "cybersecurity",
    ]
    level: Literal["easy", "medium", "advanced"]
    description: Optional[str] = None
    points: int = Field(10, ge=0)

class Game(BaseModel):
    title: str
    key: str
    description: Optional[str] = None
    points: int = Field(10, ge=0)

class Mission(BaseModel):
    title: str
    description: Optional[str] = None
    target_type: Literal["lessons", "games"]
    target_count: int = Field(1, ge=1)
    reward: Literal["badge", "stars", "points"] = "stars"
    reward_value: int = Field(5, ge=1)

class Achievement(BaseModel):
    child_id: str
    title: str
    description: Optional[str] = None
    earned_at: datetime = Field(default_factory=datetime.utcnow)

# Tracking
class Progress(BaseModel):
    child_id: str
    item_type: Literal["lesson", "game"]
    item_id: str
    score: int = Field(..., ge=0, le=100)
    stars_earned: int = Field(0, ge=0, le=3)
    points_earned: int = Field(0, ge=0)
    completed_at: datetime = Field(default_factory=datetime.utcnow)

class Recommendation(BaseModel):
    child_id: str
    recommended_type: Literal["lesson", "game", "mission"]
    ref_id: Optional[str] = None
    title: Optional[str] = None
    reason: str = ""
