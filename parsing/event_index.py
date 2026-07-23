"""
Groups a flat list of raw events by type, so the rest of parsing/ never has
to write `[e for e in events if e["type"] == "..."]` over and over.

Why this is its own file: it's used by every other parsing module
(dispatch.py, stops.py, fare.py, trip_builder.py) and by nothing outside
parsing/ — it's an internal tool of the cooking layer, not a public model.
"""
from collections import defaultdict


class EventIndex:
    """
    Wraps a raw event list and provides fast lookup by type.

    events_by_type("trip_accepted") -> list of all trip_accepted events,
    sorted by created_at. first("trip_created") -> the first event of that
    type, or None if it never fired. This mirrors the two access patterns
    every parsing module needs: "give me all of them" (dispatch rounds,
    waypoints) or "give me the one" (trip_created, trip_ended).
    """

    def __init__(self, events: list[dict]):
        self.all_events = sorted(events, key=lambda e: e.get("created_at", 0))
        self._by_type = defaultdict(list)
        for e in self.all_events:
            self._by_type[e.get("type", "")].append(e)

    def events_by_type(self, event_type: str) -> list[dict]:
        return self._by_type.get(event_type, [])

    def first(self, event_type: str) -> dict | None:
        rows = self._by_type.get(event_type, [])
        return rows[0] if rows else None

    def last(self, event_type: str) -> dict | None:
        rows = self._by_type.get(event_type, [])
        return rows[-1] if rows else None

    def present_types(self) -> set:
        return set(self._by_type.keys())
