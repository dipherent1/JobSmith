from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import (
    DatePosted,
    EmploymentType,
    ExperienceLevel,
    WorkArrangement,
    normalize_string_list,
)


class SearchPreferences(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    job_titles: list[str] = Field(min_length=1, max_length=20)
    locations: list[str] = Field(default_factory=list, max_length=20)
    work_arrangements: list[WorkArrangement] = Field(default_factory=list, max_length=3)
    employment_types: list[EmploymentType] = Field(default_factory=list, max_length=6)
    experience_level: ExperienceLevel = ExperienceLevel.UNSPECIFIED
    date_posted: DatePosted = DatePosted.ANY
    max_results_per_query: int = Field(default=50, ge=1, le=200)

    @field_validator("job_titles", "locations", mode="after")
    @classmethod
    def normalize_lists(cls, values: list[str]) -> list[str]:
        return normalize_string_list(values)

    @field_validator("work_arrangements", "employment_types", mode="after")
    @classmethod
    def deduplicate_enums(cls, values: list) -> list:
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def require_job_titles(self) -> "SearchPreferences":
        if not self.job_titles:
            raise ValueError("at least one non-empty job title is required")
        return self
