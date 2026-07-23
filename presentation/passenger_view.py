"""
Passenger & Trip Overview — the "plating" for Trip.stops and the top-level
trip identity fields. Reads only the Trip object, never raw events directly.
"""
import pandas as pd
import streamlit as st


def render_overview(trip):
    st.subheader("Passenger & Trip Info")
    info = {
        "Trip ID": trip.trip_id,
        "Passenger ID": trip.passenger_id,
        "Service Group": trip.service_group,
        "Module": trip.module_label,
        "Booked By": trip.booked_by_label,
        "Vehicle Type": trip.vehicle_type_label,
        "Corporate Trip": trip.is_corporate,
        "Pooled Trip": trip.is_pooled,
        "Pooled With": trip.pooled_with or "-",
        "Bidding Dispatch": trip.is_bidding,
        "Pre-booked": trip.is_pre_booked,
        "Promo Code (at creation)": trip.promo_code_at_creation or "-",
    }
    st.json(info)

    if trip.stops.mid_trip_update_detected:
        st.caption("ℹ️ Stop list reflects mid-trip updates from a `trip_updated` event.")

    if trip.stops.pickup:
        st.subheader("Pickup Location")
        st.dataframe(pd.DataFrame([trip.stops.pickup]).astype(str))

    if trip.stops.stops:
        st.subheader(f"Drop Locations / Stops ({len(trip.stops.stops)})")
        rows = [{
            "Stop #": s.stop_number,
            "Planned Address": s.planned_address,
            "Planned Lat": s.planned_lat,
            "Planned Lng": s.planned_lng,
            "Actual Address": s.actual_address,
            "Actual Lat": s.actual_lat,
            "Actual Lng": s.actual_lng,
            "Arrival Status": s.arrival_status,
            "Arrival Time": s.arrival_time,
        } for s in trip.stops.stops]
        st.dataframe(pd.DataFrame(rows).astype(str), use_container_width=True)
    else:
        st.info("No stop data available.")
