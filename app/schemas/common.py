from datetime import UTC, datetime
from enum import StrEnum
from urllib.parse import urlparse


class WorkArrangement(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
    OTHER = "other"


class ExperienceLevel(StrEnum):
    INTERNSHIP = "internship"
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"
    UNSPECIFIED = "unspecified"


class DatePosted(StrEnum):
    ANY = "any"
    LAST_24_HOURS = "last_24_hours"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"

    @property
    def max_age_days(self) -> int | None:
        return {
            DatePosted.ANY: None,
            DatePosted.LAST_24_HOURS: 1,
            DatePosted.LAST_7_DAYS: 7,
            DatePosted.LAST_30_DAYS: 30,
        }[self]


def utcnow() -> datetime:
    return datetime.now(UTC)


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def normalize_string_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized_values: list[str] = []
    for value in values:
        normalized = normalize_text(str(value))
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized_values.append(normalized)
    return normalized_values


def ensure_http_url(value: str) -> str:
    normalized = value.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("must be an absolute http(s) URL")
    return normalized


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
