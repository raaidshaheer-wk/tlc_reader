"""
The main "cook": takes a raw event list for ONE trip and returns one Trip
object. This is the single entry point presentation/ and comparison_view.py
should ever call — nothing outside parsing/ should touch raw events directly,
except the raw event viewer, which exists specifically to let an investigator
bypass all computed values and check the source (see Rules.md #11/#12).
"""
from parsing.event_index import EventIndex
from parsing.models import Trip
from parsing.dispatch import build_dispatch_history
from parsing.stops import build_stop_breakdown
from parsing.fare import build_fare_breakdown
from parsing.outcome import build_actual_outcome
from parsing.lookups import MODULE, BOOKED_BY, VEHICLE_TYPE, resolve
from utils.helpers import safe_get


def build_trip(events: list[dict], source_filename: str = "") -> Trip:
    idx = EventIndex(events)
    trip_created = idx.first("trip_created")
    body = trip_created["body"] if trip_created else {}

    dispatch = build_dispatch_history(idx)
    stops = build_stop_breakdown(idx)
    fare = build_fare_breakdown(idx)
    outcome = build_actual_outcome(idx, dispatch)

    corporate = safe_get(body, "corporate", default={})
    pooled_info = {}
    trip_completed = idx.first("trip_completed")
    if trip_completed:
        pooled_info = safe_get(trip_completed, "body", "trip", "pooled_info", default={})

    return Trip(
        trip_id=body.get("trip_id", 0),
        service_group=body.get("service_group_code", "UNKNOWN"),
        module_label=resolve(MODULE, body.get("module")),
        booked_by_label=resolve(BOOKED_BY, body.get("booked_by")),
        passenger_id=safe_get(body, "passenger", "id"),
        vehicle_type_label=resolve(VEHICLE_TYPE, body.get("vehicle_type")),
        is_corporate=bool(corporate.get("id")) if corporate else False,
        is_pooled=bool(pooled_info.get("pooled")),
        pooled_with=pooled_info.get("trip_ids", ""),
        is_bidding=bool(body.get("bidding")),
        is_pre_booked=bool(body.get("pre_booking")),
        promo_code_at_creation=safe_get(body, "promotion", "code", default=""),
        stops=stops,
        fare=fare,
        dispatch=dispatch,
        outcome=outcome,
        raw_events=idx.all_events,
        source_filename=source_filename,
    )
