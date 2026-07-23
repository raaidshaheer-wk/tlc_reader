"""
Reconciles planned stops (from trip_created) against what actually happened
(waypoint_status_updated events, plus the final stop which comes from
trip_ended's location instead of a waypoint).

This is the same logic the original app.py had, generalized into its own
function (SR-4) — verified against triplifecycle_multi_stops.json that for
an N-drop trip there are only N-1 waypoint_status_updated events; the final
stop is always represented by trip_ended, not a waypoint.
"""
from parsing.event_index import EventIndex
from parsing.models import StopBreakdown, StopRow
from utils.helpers import safe_get, format_timestamp


def build_stop_breakdown(idx: EventIndex) -> StopBreakdown:
    trip_created = idx.first("trip_created")
    trip_ended = idx.first("trip_ended")
    waypoint_events = idx.events_by_type("waypoint_status_updated")
    trip_updated = idx.first("trip_updated")  # INFERRED ONLY per trip_info.md §4

    body = trip_created["body"] if trip_created else {}
    pickup_locations = safe_get(body, "pickup", "location", default=[])
    drops = safe_get(body, "drop", "location", default=[])

    mid_trip_update_detected = False
    if trip_updated:
        updated_drops = safe_get(trip_updated, "body", "drop_locations", default=[])
        if updated_drops:
            drops = updated_drops
            mid_trip_update_detected = True

    waypoint_by_index = {
        e["body"].get("index"): e for e in waypoint_events
    }

    stop_rows = []
    for i, d in enumerate(drops, start=1):
        wp = waypoint_by_index.get(i)
        wp_body = wp["body"] if wp else {}
        wp_loc = wp_body.get("location", {})
        is_final = (i == len(drops))

        if is_final and trip_ended:
            ended_loc = safe_get(trip_ended, "body", "location", default={})
            actual_address = ended_loc.get("address", "-")
            actual_lat = ended_loc.get("lat")
            actual_lng = ended_loc.get("lng")
            arrival_status = "COMPLETED"
            arrival_time = format_timestamp(trip_ended["created_at"])
        else:
            actual_address = wp_loc.get("address", "-") if wp else "-"
            actual_lat = wp_loc.get("lat") if wp else None
            actual_lng = wp_loc.get("lng") if wp else None
            arrival_status = wp_body.get("status", "-") if wp else "-"
            arrival_time = format_timestamp(wp["created_at"]) if wp else "-"

        stop_rows.append(StopRow(
            stop_number=i,
            planned_address=d.get("address", ""),
            planned_lat=d.get("lat"),
            planned_lng=d.get("lng"),
            actual_address=actual_address,
            actual_lat=actual_lat,
            actual_lng=actual_lng,
            arrival_status=arrival_status,
            arrival_time=arrival_time,
        ))

    return StopBreakdown(
        pickup=pickup_locations[0] if pickup_locations else {},
        drops_planned=drops,
        stops=stop_rows,
        mid_trip_update_detected=mid_trip_update_detected,
    )
