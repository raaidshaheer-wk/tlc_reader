"""
Estimated Fare & Price File — plating for FareBreakdown.
"""
import pandas as pd
import streamlit as st


def render_fare(trip):
    st.subheader("Estimated Trip Details")
    fare = trip.fare
    if not fare:
        st.info("No fare estimate data available for this trip.")
        return

    info = {
        "Currency": fare.currency,
        "Total Distance (km)": fare.distance_km,
        "Total Duration (sec)": fare.duration_sec,
        "Number of Stops": len(trip.stops.stops),
        "Base Fare": fare.base_fare,
        "Distance Fare": fare.distance_fare,
        "Duration Fare": fare.duration_fare,
        "Waiting Fare": fare.waiting_fare,
        "Is Upfront": fare.is_upfront,
    }
    st.dataframe(pd.DataFrame([info]))

    st.subheader("Fare Price File")
    table_columns = {
        "additional_charge": ["id", "name", "amount", "type"],
        "distance_fare": ["base_fare", "distance", "km_fare"],
        "waiting_fare": ["end_time", "fare"],
    }
    rename_map = {
        "id": "ID", "name": "Name", "amount": "Amount (LKR)", "type": "Type",
        "base_fare": "Base Fare (LKR)", "distance": "Distance (km)", "km_fare": "KM Fare",
        "end_time": "End Time (s)", "fare": "Fare (LKR)",
    }
    for key in ["additional_charge", "distance_fare", "waiting_fare"]:
        items = fare.price_file_rows.get(key, [])
        st.markdown(f"**{key.replace('_', ' ').title()}**")
        if items:
            df = pd.DataFrame(items)
            cols = [c for c in table_columns[key] if c in df.columns]
            st.table(df[cols].rename(columns=rename_map))
        else:
            st.info(f"No {key.replace('_', ' ')} data available")
