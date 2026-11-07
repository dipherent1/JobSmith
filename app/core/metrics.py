from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram, Meter

from app.core.config import Settings

_instruments: "_Instruments | None" = None


class _Instruments:
    def __init__(self, meter: Meter) -> None:
        self.searches = meter.create_counter(
            "jobsmith.searches",
            unit="{search}",
            description="Search requests started or finished.",
        )
        self.search_duration = meter.create_histogram(
            "jobsmith.search.duration",
            unit="ms",
            description="End-to-end search workflow duration.",
        )
        self.source_searches = meter.create_counter(
            "jobsmith.source.searches",
            unit="{search}",
            description="Individual source searches by outcome.",
        )
        self.source_duration = meter.create_histogram(
            "jobsmith.source.duration",
            unit="ms",
            description="Individual source search duration.",
        )
        self.source_listings = meter.create_counter(
            "jobsmith.source.listings",
            unit="{listing}",
            description="Listings returned per source.",
        )
        self.duplicates_removed = meter.create_counter(
            "jobsmith.duplicates.removed",
            unit="{listing}",
            description="Duplicate listings removed.",
        )
        self.evaluations = meter.create_counter(
            "jobsmith.evaluations",
            unit="{evaluation}",
            description="Job evaluations performed.",
        )
        self.evaluation_duration = meter.create_histogram(
            "jobsmith.evaluation.duration",
            unit="ms",
            description="Job evaluation duration.",
        )
        self.llm_calls = meter.create_counter(
            "jobsmith.llm.calls",
            unit="{call}",
            description="External model calls by provider, operation, and outcome.",
        )
        self.llm_tokens = meter.create_counter(
            "jobsmith.llm.tokens",
            unit="{token}",
            description="Prompt and completion tokens used by external models.",
        )
        self.llm_cost = meter.create_counter(
            "jobsmith.llm.cost",
            unit="USD",
            description="Estimated external model cost in US dollars.",
        )

    @property
    def counters(self) -> list[Counter]:
        return [
            self.searches,
            self.source_searches,
            self.source_listings,
            self.duplicates_removed,
            self.evaluations,
            self.llm_calls,
            self.llm_tokens,
            self.llm_cost,
        ]

    @property
    def histograms(self) -> list[Histogram]:
        return [
            self.search_duration,
            self.source_duration,
            self.evaluation_duration,
        ]


def get_instruments() -> _Instruments:
    global _instruments
    if _instruments is None:
        _instruments = _Instruments(metrics.get_meter("jobsmith"))
    return _instruments


def configure_metrics(settings: Settings) -> None:
    if not settings.metrics_enabled:
        return

    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import (
        ConsoleMetricExporter,
        PeriodicExportingMetricReader,
    )

    readers = []
    if settings.metrics_exporter == "console":
        readers.append(
            PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=settings.metrics_export_interval_ms,
            )
        )

    provider = MeterProvider(metric_readers=readers)
    global _instruments
    _instruments = None
    metrics.set_meter_provider(provider)
    _instruments = _Instruments(provider.get_meter("jobsmith"))


def record_search_started() -> None:
    get_instruments().searches.add(1, {"status": "started"})


def record_search_finished(duration_ms: float, status: str) -> None:
    instruments = get_instruments()
    instruments.searches.add(1, {"status": status})
    instruments.search_duration.record(duration_ms, {"status": status})


def record_source_search(
    source: str,
    duration_ms: float,
    outcome: str,
    listing_count: int,
) -> None:
    instruments = get_instruments()
    attributes = {"source": source, "outcome": outcome}
    instruments.source_searches.add(1, attributes)
    instruments.source_duration.record(duration_ms, attributes)
    instruments.source_listings.add(listing_count, {"source": source})


def record_duplicates_removed(count: int) -> None:
    get_instruments().duplicates_removed.add(count)


def record_evaluation(duration_ms: float, outcome: str) -> None:
    instruments = get_instruments()
    instruments.evaluations.add(1, {"outcome": outcome})
    instruments.evaluation_duration.record(duration_ms, {"outcome": outcome})


def record_llm_call(
    provider: str,
    operation: str,
    outcome: str,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
) -> None:
    instruments = get_instruments()
    attributes = {"provider": provider, "operation": operation, "outcome": outcome}
    instruments.llm_calls.add(1, attributes)
    if input_tokens:
        instruments.llm_tokens.add(input_tokens, {**attributes, "direction": "input"})
    if output_tokens:
        instruments.llm_tokens.add(output_tokens, {**attributes, "direction": "output"})
    if cost_usd:
        instruments.llm_cost.add(cost_usd, attributes)
