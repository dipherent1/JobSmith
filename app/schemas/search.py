from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.candidate import CandidateProfile
from app.schemas.common import ensure_utc, utcnow
from app.schemas.job import JobListing
from app.schemas.preferences import SearchPreferences


class SearchStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class SearchRequest(BaseModel):
    candidate: CandidateProfile
    preferences: SearchPreferences


class SourceError(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    error_type: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=1_000)
    retryable: bool = False
    occurred_at: datetime = Field(default_factory=utcnow)

    @field_validator("occurred_at")
    @classmethod
    def normalize_occurred_at(cls, value: datetime) -> datetime:
        normalized = ensure_utc(value)
        assert normalized is not None
        return normalized


class SearchMetadata(BaseModel):
    search_timestamp: datetime = Field(default_factory=utcnow)
    sources_searched: list[str] = Field(default_factory=list)
    listings_found: int = Field(default=0, ge=0)
    duplicates_removed: int = Field(default=0, ge=0)
    jobs_evaluated: int = Field(default=0, ge=0)
    source_errors: list[SourceError] = Field(default_factory=list)
    duration_ms: float = Field(default=0.0, ge=0)
    trace_id: str | None = None

    @field_validator("search_timestamp")
    @classmethod
    def normalize_search_timestamp(cls, value: datetime) -> datetime:
        normalized = ensure_utc(value)
        assert normalized is not None
        return normalized


class JobMatch(BaseModel):
    listing: JobListing
    overall_score: float = Field(ge=0, le=100)
    skills_match: float = Field(ge=0, le=100)
    experience_match: float = Field(ge=0, le=100)
    location_match: float = Field(ge=0, le=100)
    explanation: str = Field(min_length=1, max_length=4_000)
    missing_qualifications: list[str] = Field(default_factory=list, max_length=100)
    disqualifying_requirements: list[str] = Field(default_factory=list, max_length=50)
    matched_required_skills: list[str] = Field(default_factory=list, max_length=200)
    missing_required_skills: list[str] = Field(default_factory=list, max_length=200)
    matched_preferred_skills: list[str] = Field(default_factory=list, max_length=200)
    career_category: str | None = Field(default=None, max_length=200)


class SearchResponse(BaseModel):
    search_id: UUID
    status: SearchStatus
    results: list[JobMatch] = Field(default_factory=list)
    metadata: SearchMetadata


class JobListResponse(BaseModel):
    items: list[JobListing] = Field(default_factory=list)
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
