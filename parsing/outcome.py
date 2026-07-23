"""
Builds the "what actually happened" facts for a completed trip: cost,
wait times, distance, payment, and the requested-vs-assigned vehicle
mismatch discovered in trip_info.md (motor_model_id vs original_motor_model_id).

Depends on dispatch.py's resolved real_driver_id (SR-1) rather than grabbing
trip_accepted directly — this is the payoff of doing that resolution once,
in one place, instead of every module re-deriving "who's the driver."
"""
from parsing.event_index import EventIndex
from parsing.models import ActualOutcome, DispatchHistory
from parsing.lookups import VEHICLE_TYPE, PAYMENT_METHOD, resolve
from utils.helpers import safe_get, format_timestamp, seconds_diff


def build_actual_outcome(idx: EventIndex, dispatch: DispatchHistory) -> ActualOutcome | None:
    trip_completed = idx.first("trip_completed")
    trip_ended = idx.first("trip_ended")
    if not trip_completed and not trip_ended:
        return None

    completed = trip_completed["body"] if trip_completed else {}
    ended = trip_ended["body"] if trip_ended else {}
    trip_info = safe_get(completed, "trip", default={})

    trip_accepted_events = idx.events_by_type("trip_accepted")
    trip_started = idx.first("trip_started")
    driver_arrived = idx.first("driver_arrived")
    trip_end_notif = idx.first("trip_end_notification")

    # find the trip_accepted event matching the resolved real driver (SR-1),
    # not just "the first one" — needed for an accurate passenger_wait_time
    real_accept_event = None
    if dispatch.real_driver_id is not None:
        for a in trip_accepted_events:
            if a["body"].get("driver_id") == dispatch.real_driver_id:
                real_accept_event = a
                break

    passenger_wait_time = None
    if real_accept_event and trip_started:
        passenger_wait_time = seconds_diff(
            trip_started["created_at"], real_accept_event["created_at"]
        )

    driver_wait_time = None
    if driver_arrived and trip_started:
        driver_wait_time = seconds_diff(
            trip_started["created_at"], driver_arrived["created_at"]
        )

    end_notif_gap = None
    if trip_end_notif and trip_ended:
        end_notif_gap = seconds_diff(
            trip_ended["created_at"], trip_end_notif["created_at"]
        )

    meter_details = safe_get(ended, "meter_details", "travel_details", default={})
    travel_info = safe_get(ended, "travel_info", default={})

    requested_model = trip_info.get("original_motor_model_id")
    assigned_model = trip_info.get("motor_model_id")

    return ActualOutcome(
        driver_id=ended.get("driver_id", trip_info.get("driver_id")) or dispatch.real_driver_id,
        actual_pickup_address=safe_get(trip_info, "actual_pickup", "address"),
        actual_drop_address=safe_get(trip_info, "actual_drop", "address"),
        trip_start_time=format_timestamp(trip_started["created_at"]) if trip_started else None,
        driver_arrived_time=format_timestamp(driver_arrived["created_at"]) if driver_arrived else None,
        trip_end_notification_time=format_timestamp(trip_end_notif["created_at"]) if trip_end_notif else None,
        passenger_wait_time_sec=passenger_wait_time,
        driver_wait_time_sec=driver_wait_time,
        end_notif_to_ended_gap_sec=end_notif_gap,
        distance_travelled_m=meter_details.get("distance_travelled"),
        waiting_time_sec=meter_details.get("waiting_time"),
        trip_cost=trip_info.get("trip_cost"),
        promo_code=trip_info.get("promo_code") or None,
        discount=trip_info.get("discount"),
        tip=trip_info.get("total_tip"),
        payment_method_label=resolve(PAYMENT_METHOD, safe_get(trip_info, "payment", 0, "method")),
        actual_duration_sec=travel_info.get("actual_duration"),
        requested_vehicle_label=resolve(VEHICLE_TYPE, requested_model),
        assigned_vehicle_label=resolve(VEHICLE_TYPE, assigned_model),
        vehicle_mismatch=(
            requested_model is not None
            and assigned_model is not None
            and requested_model != assigned_model
        ),
    )
