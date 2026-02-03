from dataclasses import dataclass, field


@dataclass
class VenueMetrics:
    """Track scraping metrics for each venue."""
    name: str
    event_count: int = 0
    new_events: int = 0
    errors: int = 0
    error_messages: list = field(default_factory=list)
    duration_ms: float = 0.0
