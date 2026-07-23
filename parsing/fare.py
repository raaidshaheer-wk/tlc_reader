"""
Builds the estimated-fare breakdown from trip_fare_updated. Note: a trip can
have multiple trip_fare_updated events (fare recalculated); we use the last
one, since it reflects the most up-to-date estimate before the trip started.
"""
from parsing.event_index import EventIndex
from parsing.models import FareBreakdown
from utils.helpers import safe_get


def build_fare_breakdown(idx: EventIndex) -> FareBreakdown | None:
    fare_event = idx.last("trip_fare_updated")
    if not fare_event:
        return None

    fare_list = safe_get(fare_event, "body", "fare_details", default=[])
    if not fare_list:
        return None
    f = fare_list[0]
    est = safe_get(f, "estimated_fare", "fare_info", default={})
    price_file = safe_get(f, "price_file", default={})

    return FareBreakdown(
        currency=f.get("currency_code", ""),
        distance_km=f.get("distance"),
        duration_sec=f.get("duration"),
        base_fare=est.get("min_fare"),
        distance_fare=str(safe_get(est, "fare_breakdown", "distance_fare")),
        duration_fare=str(safe_get(est, "fare_breakdown", "duration_fare")),
        waiting_fare=str(est.get("waiting_fare")),
        is_upfront=bool(f.get("is_upfront")),
        price_file_rows={
            "additional_charge": price_file.get("additional_charge", []),
            "distance_fare": price_file.get("distance_fare", []),
            "waiting_fare": price_file.get("waiting_fare", []),
        },
    )
