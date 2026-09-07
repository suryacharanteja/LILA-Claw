"""Deterministic offline doubles: no external effects or network clients."""
from dataclasses import dataclass, field

@dataclass
class FixtureBrowser:
    calls: list[str] = field(default_factory=list)

    def discover(self):
        self.calls.append("discover")
        return [{"external_id": "fixture-job-001", "title": "Python engineer"}]

@dataclass
class FixtureProvider:
    calls: int = 0

    def draft(self, confirmed_facts: dict[str, str]) -> str:
        self.calls += 1
        if not confirmed_facts:
            raise ValueError("confirmed facts required")
        return "\n".join(f"{key}: {value}" for key, value in sorted(confirmed_facts.items()))
