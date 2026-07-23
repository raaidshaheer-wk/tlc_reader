"""
Glossary — a plain-English reference for every coded value and event type
used elsewhere in the app. Pulls directly from parsing/lookups.py so there's
exactly one source of truth: if a code's meaning is ever corrected there,
this view updates automatically, nothing to keep in sync by hand.
"""
import pandas as pd
import streamlit as st

from parsing.lookups import (
    BOOKED_BY, BOOKING_FROM, MODULE, PAYMENT_METHOD, VEHICLE_TYPE,
    ASSIGN_TYPE, SELECTION_TYPE, TRIP_ACCEPT_TYPE, CANCELLED_FROM,
    CANCEL_TYPE, TRIP_STATUS, BOOKING_STATUS, TRAVEL_STATUS, LOYALTY_TIER,
)

# Plain-English description of every event type this dashboard understands.
# Kept here (not in lookups.py) because these describe *events*, not coded
# field values — a different kind of glossary entry, so it gets its own table.
EVENT_TYPE_DESCRIPTIONS = {
    "trip_created": "Fires once, when the trip request is first made. Contains the planned pickup/drops, passenger, fare filters, and booking metadata.",
    "trip_fare_updated": "Fires 1+ times — the estimated fare (re)calculation, including the full price-file breakdown.",
    "driver_selected": "Fires once per dispatch round — the list of driver candidates the system is considering.",
    "driver_assigned": "Fires once per dispatch round — the specific driver chosen from the candidates in the matching driver_selected event.",
    "trip_received_by_driver": "Fires once per driver notified of the trip request.",
    "trip_accepted": "Fires once per driver who accepts the trip. Can fire more than once if an earlier driver later cancels (see 'AFTER_ACCEPTED' rejection reason) — the dashboard resolves the real driver via trip_started, not the first trip_accepted.",
    "trip_rejected_by_driver": "Fires once per driver rejection, whatever the reason (system rejection, blast timeout, or cancelling after accepting).",
    "blast_trip_rejected_by_all_drivers": "Fires when an entire batch of blast-dispatched drivers rejects/times out, forcing a new dispatch round.",
    "trip_pin_required": "Fires when PIN verification is required — seen for both trip start and trip end.",
    "driver_arrived": "Fires once, when the driver reaches the pickup location.",
    "trip_started": "Fires exactly once, for the driver who actually began the trip. This is the dashboard's source of truth for 'who really did the trip.'",
    "waypoint_status_updated": "Fires once per intermediate stop reached on a multi-drop trip (not the final stop — that comes from trip_ended).",
    "trip_end_notification": "Fires once, when the driver is near the final drop-off.",
    "trip_ended": "Fires once, when the trip physically ends — includes final location, meter details, and actual travel stats.",
    "trip_completed": "Fires once, the final billing/settlement record — trip cost, discount, payment method, pooling info.",
    "trip_updated": "Not yet confirmed in a real sample — expected to carry mid-trip stop changes (drop_locations).",
    "trip_cancelled": "Not yet seen in any sample — full passenger/dispatcher cancellation, distinct from a driver rejecting.",
}


def _table(title, mapping, caption=None):
    st.markdown(f"**{title}**")
    if caption:
        st.caption(caption)
    df = pd.DataFrame(
        [{"Code": k, "Meaning": v} for k, v in sorted(mapping.items(), key=lambda x: (x[0] is None, x[0]))]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_glossary():
    st.subheader("Event Types")
    st.caption("What each event in the raw log means, in the order it typically appears in a trip's lifecycle.")
    df = pd.DataFrame(
        [{"Event Type": k, "Meaning": v} for k, v in EVENT_TYPE_DESCRIPTIONS.items()]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Coded Field Values")
    st.caption("Every raw integer/code shown elsewhere in this app, resolved to a label. Source: official TLC glossary.")

    col1, col2 = st.columns(2)
    with col1:
        _table("Booked By (trip_created.booked_by)", BOOKED_BY)
        _table("Booking From", BOOKING_FROM, "How/where the booking channel was — distinct from 'Booked By.'")
        _table("Module", MODULE)
        _table("Payment Method", PAYMENT_METHOD)
        _table("Vehicle Type", VEHICLE_TYPE)
        _table("Assign Type", ASSIGN_TYPE)
    with col2:
        _table("Selection Type", SELECTION_TYPE, "Dispatch-algorithm reason code (DH/FH/MB are internal matching-mode abbreviations).")
        _table("Trip Accept Type", TRIP_ACCEPT_TYPE)
        _table("Cancelled From", CANCELLED_FROM)
        _table("Cancel Type", CANCEL_TYPE)
        _table("Trip Status", TRIP_STATUS)
        _table("Booking Status", BOOKING_STATUS)
        _table("Loyalty Tier (driver)", LOYALTY_TIER)

    st.divider()
    _table("Travel Status", TRAVEL_STATUS)

    st.divider()
    st.info(
        "Not every code above has been seen in a real sample yet — some come "
        "straight from the official glossary and are here for reference. "
        "See `trip_info.md` for which fields are confirmed vs. still unconfirmed."
    )
