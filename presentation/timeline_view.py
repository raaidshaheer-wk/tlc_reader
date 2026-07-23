"""
Complete Trip Events Timeline — the same all-event chronological table as
the original app, plus a per-event summary line. This is a companion to
raw_events_view.py: this one tells the *story* in order; that one is the
grouped ground-truth reference for verification (Rules.md #11/#12).
"""
import json
import pandas as pd
import streamlit as st
from utils.helpers import safe_get, format_timestamp

EVENT_SUMMARY = {
    "trip_created": lambda b: f"Passenger: {safe_get(b,'passenger','id')} | PIN: {b.get('pin')}",
    "trip_fare_updated": lambda b: f"Fare: {safe_get(b,'fare_details',0,'estimated_fare','fare_info','min_fare')} {safe_get(b,'fare_details',0,'currency_code')} | Dist: {safe_get(b,'fare_details',0,'distance')}km",
    "driver_selected": lambda b: f"Drivers considered: {len(b.get('drivers', []))}",
    "driver_assigned": lambda b: f"Assigned Driver: {b.get('driver_id')} | ETA: {b.get('eta')}s | Blast: {b.get('blast_dispatch')}",
    "trip_received_by_driver": lambda b: f"Driver {b.get('driver_id')} received the trip",
    "trip_accepted": lambda b: f"Driver {b.get('driver_id')} accepted at {safe_get(b,'location','address')}",
    "trip_rejected_by_driver": lambda b: f"Driver {b.get('driver_id')} rejected — Reason: {b.get('rejection_type')}",
    "blast_trip_rejected_by_all_drivers": lambda b: f"All {len(b.get('drivers_status', []))} drivers in this round rejected — redispatch triggered",
    "trip_pin_required": lambda b: f"PIN required: {b.get('pin_type')}",
    "driver_arrived": lambda b: f"Driver {b.get('driver_id')} arrived at {safe_get(b,'location','address')}",
    "trip_updated": lambda b: f"Update type: {b.get('update_type')} | Stops: {len(b.get('drop_locations', []))}",
    "trip_started": lambda b: f"Driver {b.get('driver_id')} started at {safe_get(b,'location','address')}",
    "waypoint_status_updated": lambda b: f"Stop {b.get('index')} — {b.get('status')} at {safe_get(b,'location','address')}",
    "trip_end_notification": lambda b: f"Driver {b.get('driver_id')} near end at {safe_get(b,'location','address')}",
    "trip_ended": lambda b: f"Fare: {safe_get(b,'final_trip_fare','final_trip_fare')} | Dist: {safe_get(b,'meter_details','travel_details','distance_travelled')}m | Duration: {safe_get(b,'travel_info','actual_duration')}s",
    "trip_completed": lambda b: f"Cost: {safe_get(b,'trip','trip_cost')} | Surge: {safe_get(b,'surge','value')} | Payment: {safe_get(b,'trip','payment',0,'method')}",
}

CATEGORY = {
    "driver_selected": "Driver Event", "driver_assigned": "Driver Event",
    "trip_received_by_driver": "Driver Event", "trip_accepted": "Driver Event",
    "trip_rejected_by_driver": "Driver Event", "driver_arrived": "Driver Event",
    "blast_trip_rejected_by_all_drivers": "Driver Event",
    "waypoint_status_updated": "Waypoint Event",
    "trip_fare_updated": "Fare Event",
    "trip_pin_required": "Security Event",
}


def render_timeline(trip):
    st.subheader("Complete Trip Events Timeline")
    rows = []
    for e in trip.raw_events:
        body = e.get("body", {})
        etype = e.get("type", "")
        try:
            summary = EVENT_SUMMARY.get(etype, lambda b: "")(body)
        except Exception:
            summary = ""
        rows.append({
            "Timestamp": format_timestamp(e.get("created_at")),
            "Event Type": etype,
            "Category": CATEGORY.get(etype, "Trip Event"),
            "Driver ID": safe_get(body, "driver_id", default="-"),
            "Location": safe_get(body, "location", "address", default="-"),
            "Summary": summary,
        })

    if not rows:
        st.info("No events to show.")
        return

    df = pd.DataFrame(rows)
    df.sort_values("Timestamp", inplace=True)
    st.dataframe(df, use_container_width=True)
