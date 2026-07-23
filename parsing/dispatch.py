"""
Reconstructs the dispatch history of a trip: every round of
driver_selected -> driver_assigned -> trip_received_by_driver ->
trip_accepted/trip_rejected_by_driver, however many rounds it took.

This is where SR-1 (who really drove), SR-2 (N rounds, not 1-2), and SR-3
(accept-then-cancel flag) live — all three are dispatch-mechanics questions,
not fare or stop questions, so they belong together in one module (this is
exactly the "single clear responsibility" gate from the function-definition
framework: dispatch reconstruction is one job).
"""
from parsing.event_index import EventIndex
from parsing.models import DispatchHistory, DispatchRound
from utils.helpers import safe_get


def build_dispatch_history(idx: EventIndex) -> DispatchHistory:
    history = DispatchHistory()

    selected_events = idx.events_by_type("driver_selected")
    assigned_events = idx.events_by_type("driver_assigned")
    rejected_events = idx.events_by_type("trip_rejected_by_driver")
    accepted_events = idx.events_by_type("trip_accepted")
    trip_started = idx.first("trip_started")

    # --- SR-2: reconstruct every round, in order, how many ever happened ---
    # We pair driver_selected[i] with driver_assigned[i] by position, since
    # both fire once per dispatch round and in the same order. This holds
    # across every sample checked so far (up to 6 rounds in parcel.json).
    for i, sel in enumerate(selected_events):
        assigned = assigned_events[i] if i < len(assigned_events) else None
        driver_id = assigned["body"].get("driver_id") if assigned else None

        # did this driver get accepted, rejected, or is the round's outcome
        # unclear (e.g. log cuts off mid-round)?
        outcome = "unknown"
        if driver_id is not None:
            was_accepted = any(
                a["body"].get("driver_id") == driver_id for a in accepted_events
            )
            was_rejected = any(
                r["body"].get("driver_id") == driver_id for r in rejected_events
            )
            if was_accepted:
                outcome = "accepted"
            elif was_rejected:
                outcome = "rejected"

        history.rounds.append(DispatchRound(
            round_number=i + 1,
            candidates=sel["body"].get("drivers", []),
            assigned_driver_id=driver_id,
            assigned_at=assigned.get("created_at") if assigned else None,
            outcome=outcome,
        ))

    history.total_rejections = len(rejected_events)
    if assigned_events:
        history.bidding = bool(assigned_events[0]["body"].get("bidding"))
        history.blast_dispatch = bool(assigned_events[0]["body"].get("blast_dispatch"))

    # --- SR-1: resolve the real driver ---
    # Primary rule: trip_started fires exactly once, only for the driver who
    # actually began the trip. Trust it over trip_accepted, which can fire
    # multiple times if a driver cancels after accepting (see SR-3 below).
    if trip_started:
        history.real_driver_id = trip_started["body"].get("driver_id")
    elif accepted_events:
        # Fallback: trip never started (e.g. cancelled before pickup) —
        # the most recent acceptance attempt is the best available signal.
        history.real_driver_id = accepted_events[-1]["body"].get("driver_id")

    # --- SR-3: flag accept-then-cancel pattern ---
    # For every driver who was accepted, check if that same driver later
    # shows up in trip_rejected_by_driver with rejection_type AFTER_ACCEPTED.
    # If so, this trip had a driver back out post-acceptance — a genuine
    # dispute-relevant fact, independent of who the eventual real driver was.
    accepted_driver_ids = {a["body"].get("driver_id") for a in accepted_events}
    for r in rejected_events:
        if (
            r["body"].get("driver_id") in accepted_driver_ids
            and r["body"].get("rejection_type") == "AFTER_ACCEPTED"
        ):
            history.cancelled_after_accept = True
            break

    return history
