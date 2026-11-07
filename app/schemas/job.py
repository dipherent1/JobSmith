from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import (
    EmploymentType,
    ExperienceLevel,
    WorkArrangement,
    ensure_http_url,
    ensure_utc,
    normalize_string_list,
    utcnow,
)

SalaryPeriod = Literal["year", "month", "week", "day", "hour", "unknown"]


class Salary(BaseModel):
    minimum: float | None = Field(default=None, ge=0)
    maximum: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    period: SalaryPeriod = "unknown"

    @model_validator(mode="after")
    def validate_range(self) -> "Salary":
        if self.minimum is not None and self.maximum is not None and self.maximum < self.minimum:
            raise ValueError("maximum salary must not be less than minimum salary")
        return self


class JobListing(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    external_id: str | None = Field(default=None, max_length=500)
    source: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    company: str = Field(min_length=1, max_length=300)
    location: str | None = Field(default=None, max_length=300)
    work_arrangement: WorkArrangement | None = None
    employment_type: EmploymentType | None = None
    experience_level: ExperienceLevel | None = None
    description: str = Field(default="", max_length=100_000)
    required_skills: list[str] = Field(default_factory=list, max_length=200)
    preferred_skills: list[str] = Field(default_factory=list, max_length=200)
    salary: Salary | None = None
    date_posted: datetime | None = None
    application_url: str = Field(max_length=2_000)
    source_url: str | None = Field(default=None, max_length=2_000)
    source_query: str | None = Field(default=None, max_length=500)
    retrieved_at: datetime = Field(default_factory=utcnow)

    @field_validator("required_skills", "preferred_skills", mode="after")
    @classmethod
    def normalize_skills(cls, values: list[str]) -> list[str]:
        return normalize_string_list(values)

    @field_validator("application_url", "source_url")
    @classmethod
    def validate_urls(cls, value: str | None) -> str | None:
        return ensure_http_url(value) if value else None

    @field_validator("date_posted", "retrieved_at")
    @classmethod
    def normalize_dates(cls, value: datetime | None) -> datetime | None:
        return ensure_utc(value)
