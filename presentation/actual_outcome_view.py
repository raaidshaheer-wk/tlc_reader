"""
Actual Trip Details — plating for ActualOutcome. Surfaces the vehicle
mismatch and payment method label discovered during schema exploration.
"""
import streamlit as st


def render_actual_outcome(trip):
    st.subheader("Actual Trip Details")
    outcome = trip.outcome
    if not outcome:
        st.info("This trip has no completion data (not finished, or cancelled before completion).")
        return

    if outcome.vehicle_mismatch:
        st.warning(
            f"⚠️ Vehicle mismatch: passenger requested "
            f"**{outcome.requested_vehicle_label}**, but was assigned "
            f"**{outcome.assigned_vehicle_label}**."
        )

    if trip.dispatch.cancelled_after_accept:
        st.warning(
            "⚠️ A driver accepted this trip and later cancelled "
            "(`AFTER_ACCEPTED`) before the driver shown below completed it. "
            "See the Dispatch tab for the full sequence."
        )

    info = {
        "Driver ID (resolved via trip_started)": outcome.driver_id,
        "Actual Pickup Address": outcome.actual_pickup_address,
        "Actual Drop Address": outcome.actual_drop_address,
        "Trip Start Time": outcome.trip_start_time,
        "Driver Arrived Time": outcome.driver_arrived_time,
        "Trip End Notification Time": outcome.trip_end_notification_time,
        "Passenger Wait Time (sec)": outcome.passenger_wait_time_sec,
        "Driver Wait Time at Pickup (sec)": outcome.driver_wait_time_sec,
        "End Notification to Fare Finalization Gap (sec)": outcome.end_notif_to_ended_gap_sec,
        "Distance Travelled (m)": outcome.distance_travelled_m,
        "Waiting Time (sec)": outcome.waiting_time_sec,
        "Total Trip Cost": outcome.trip_cost,
        "Promotion Code": outcome.promo_code,
        "Discount": outcome.discount,
        "Tip": outcome.tip,
        "Payment Method": outcome.payment_method_label,
        "Actual Duration (sec)": outcome.actual_duration_sec,
        "Requested Vehicle": outcome.requested_vehicle_label,
        "Assigned Vehicle": outcome.assigned_vehicle_label,
    }
    st.json(info)
