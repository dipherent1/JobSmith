from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.schemas import (
    CandidateProfile,
    JobListing,
    Salary,
    SearchPreferences,
    SearchRequest,
    WorkExperienceEntry,
)
from app.schemas.common import EmploymentType, WorkArrangement


def test_candidate_normalizes_resume_and_skills() -> None:
    candidate = CandidateProfile(
        resume_text="  Software   engineer  ",
        skills=[" Python ", "python", "SQL", ""],
        years_experience=4,
    )

    assert candidate.resume_text == "Software engineer"
    assert candidate.skills == ["Python", "SQL"]


def test_candidate_requires_usable_content() -> None:
    with pytest.raises(ValidationError):
        CandidateProfile(skills=[])


def test_candidate_rejects_invalid_experience_dates() -> None:
    with pytest.raises(ValidationError):
        WorkExperienceEntry(
            title="Engineer",
            company="Acme",
            start_date=date(2024, 1, 1),
            end_date=date(2023, 1, 1),
        )


def test_candidate_rejects_negative_years() -> None:
    with pytest.raises(ValidationError):
        CandidateProfile(skills=["Python"], years_experience=-1)


def test_preferences_normalize_and_deduplicate() -> None:
    preferences = SearchPreferences(
        job_titles=["  Backend Engineer ", "backend engineer", ""],
        locations=[" Remote ", "remote"],
        work_arrangements=["remote", "remote"],
        employment_types=["full_time", "full_time"],
    )

    assert preferences.job_titles == ["Backend Engineer"]
    assert preferences.locations == ["Remote"]
    assert preferences.work_arrangements == [WorkArrangement.REMOTE]
    assert preferences.employment_types == [EmploymentType.FULL_TIME]


def test_preferences_require_a_job_title() -> None:
    with pytest.raises(ValidationError):
        SearchPreferences(job_titles=["   "])


def test_job_listing_validates_and_normalizes() -> None:
    listing = JobListing(
        source="remotive",
        title="Backend Engineer",
        company="Acme",
        application_url="https://example.com/jobs/1",
        source_url="https://example.com/jobs/1",
        required_skills=[" Python ", "python", "FastAPI"],
        date_posted=datetime(2026, 1, 1, 12, 0),
    )

    assert listing.required_skills == ["Python", "FastAPI"]
    assert listing.date_posted is not None
    assert listing.date_posted.tzinfo is not None


def test_job_listing_rejects_invalid_url() -> None:
    with pytest.raises(ValidationError):
        JobListing(
            source="remotive",
            title="Backend Engineer",
            company="Acme",
            application_url="not-a-url",
        )


def test_salary_rejects_inverted_range() -> None:
    with pytest.raises(ValidationError):
        Salary(minimum=100, maximum=50)


def test_search_request_round_trips() -> None:
    request = SearchRequest(
        candidate=CandidateProfile(skills=["Python"], years_experience=3),
        preferences=SearchPreferences(
            job_titles=["Backend Engineer"],
            locations=["Remote"],
            work_arrangements=["remote"],
        ),
    )

    assert SearchRequest.model_validate(request.model_dump()) == request
