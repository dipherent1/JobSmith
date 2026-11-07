from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import ensure_http_url, normalize_string_list, normalize_text


class EducationEntry(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    institution: str = Field(min_length=1, max_length=300)
    degree: str | None = Field(default=None, max_length=200)
    field_of_study: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    details: str | None = Field(default=None, max_length=4_000)

    @model_validator(mode="after")
    def validate_dates(self) -> "EducationEntry":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class WorkExperienceEntry(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = Field(default=None, max_length=10_000)
    skills: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("skills", mode="after")
    @classmethod
    def normalize_skills(cls, values: list[str]) -> list[str]:
        return normalize_string_list(values)

    @model_validator(mode="after")
    def validate_dates(self) -> "WorkExperienceEntry":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class ProjectEntry(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    skills: list[str] = Field(default_factory=list, max_length=100)
    url: str | None = Field(default=None, max_length=2_000)

    @field_validator("skills", mode="after")
    @classmethod
    def normalize_skills(cls, values: list[str]) -> list[str]:
        return normalize_string_list(values)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        return ensure_http_url(value) if value else None


class CandidateProfile(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    resume_text: str | None = Field(default=None, max_length=100_000)
    skills: list[str] = Field(default_factory=list, max_length=200)
    education: list[EducationEntry] = Field(default_factory=list, max_length=20)
    work_experience: list[WorkExperienceEntry] = Field(default_factory=list, max_length=50)
    projects: list[ProjectEntry] = Field(default_factory=list, max_length=50)
    years_experience: float | None = Field(default=None, ge=0, le=60)

    @field_validator("resume_text", mode="before")
    @classmethod
    def normalize_resume_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_text(value)
        return normalized or None

    @field_validator("skills", mode="after")
    @classmethod
    def normalize_skills(cls, values: list[str]) -> list[str]:
        return normalize_string_list(values)

    @model_validator(mode="after")
    def require_usable_profile(self) -> "CandidateProfile":
        if not any(
            [
                self.resume_text,
                self.skills,
                self.education,
                self.work_experience,
                self.projects,
                self.years_experience is not None,
            ]
        ):
            raise ValueError(
                "candidate profile must include resume text or at least one structured field"
            )
        return self
