from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid

class Platform(str, Enum):
    TWITTER = "twitter"
    REDDIT = "reddit"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"

class IntentClass(str, Enum):
    COMPLAINT = "complaint"
    PRAISE = "praise"
    QUESTION = "question"
    NEUTRAL_MENTION = "neutral_mention"
    COMPETITOR_ATTACK = "competitor_attack"
    CRISIS_SIGNAL = "crisis_signal"
    VIRAL_OPPORTUNITY = "viral_opportunity"

class ActionType(str, Enum):
    REPLY = "reply"
    POST = "post"
    REPOST = "repost"
    SKIP = "skip"
    ESCALATE = "escalate"

class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"

class EngagementMetrics(BaseModel):
    likes: int = 0
    replies: int = 0
    shares: int = 0
    impressions: int = 0

class SignalClassification(BaseModel):
    intent: IntentClass
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    entities: list[str] = []
    is_crisis: bool = False

class SocialSignal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: Platform
    external_id: str
    author_id: str
    author_username: str
    content: str
    media_urls: list[str] = []
    engagement: EngagementMetrics = Field(default_factory=EngagementMetrics)
    classification: Optional[SignalClassification] = None
    parent_id: Optional[str] = None
    thread_depth: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    received_at: datetime = Field(default_factory=datetime.utcnow)

class ModerationResult(BaseModel):
    passed: bool
    perspective_score: float = 0.0
    brand_safety_score: float = 0.0
    persona_consistency_score: float = 0.0
    flags: list[str] = []
    reason: Optional[str] = None

class AgentAction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_id: str
    agent_id: str
    action_type: ActionType
    draft_content: str
    final_content: Optional[str] = None
    moderation: Optional[ModerationResult] = None
    review_status: ReviewStatus = ReviewStatus.PENDING
    human_edits: Optional[str] = None
    published_at: Optional[datetime] = None
    outcome: Optional[EngagementMetrics] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PersonaConfig(BaseModel):
    account_id: str
    display_name: str
    platform: Platform
    tone_primary: str = "professional"
    tone_secondary: str = "helpful"
    voice_examples: list[str] = []
    topics: list[str] = []
    avoid_topics: list[str] = []
    approved_hashtags: list[str] = []
    max_posts_per_day: int = 10
    min_gap_hours: float = 1.0
    approval_required: bool = True
