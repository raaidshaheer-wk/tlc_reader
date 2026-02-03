import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime

st.set_page_config(page_title="Trip Dashboard", layout="wide")
st.title("PickMe Trip Dashboard")

# --- Helper Functions ---
def safe_get(d, *keys, default=None):
    """Safe get nested dictionary/list values"""
    for key in keys:
        if isinstance(d, list) and isinstance(key, int):
            if key < len(d):
                d = d[key]
            else:
                return default
        elif isinstance(d, dict):
            d = d.get(key, default)
        else:
            return default
    return d

def format_timestamp(ts):
    try:
        if ts > 1e12:  # milliseconds
            ts = ts / 1000
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return ts

# --- User Input ---
trip_id_input = st.text_input("Enter Trip ID", "")
if trip_id_input:
    url = f"https://tlc-event-reader.pickme.lk/triplifecycle?trip_id={trip_id_input}"
    response = requests.get(url)
    if response.status_code != 200:
        st.error("Failed to fetch trip data. Check Trip ID.")
    else:
        data = response.json()

        # --- Separate events by type ---
        trip_created_event = next((e for e in data if e["type"] == "trip_created"), None)
        trip_fare_event = next((e for e in data if e["type"] == "trip_fare_updated"), None)
        trip_completed_event = next((e for e in data if e["type"] == "trip_completed"), None)
        trip_ended_event = next((e for e in data if e["type"] == "trip_ended"), None)
        driver_events = [e for e in data if "driver_id" in e["body"]]

        # --- Passenger & Trip Info ---
        st.header("Passenger & Trip Info")
        if trip_created_event:
            body = trip_created_event["body"]
            pickup = safe_get(body, "pickup", "location", 0, default={})
            drop = safe_get(body, "drop", "location", 0, default={})
            passenger_info = {
                "Passenger ID": safe_get(body, "passenger", "id"),
                "PIN": safe_get(body, "pin"),
                "Seats": safe_get(body, "seat_requirement"),
                "Pre-booking": safe_get(body, "pre_booking"),
                "Service Group": safe_get(body, "service_group_code"),
                "Pickup Address": pickup.get("address", ""),
                "Drop Address": drop.get("address", ""),
                "Pickup Lat": pickup.get("lat"),
                "Pickup Lng": pickup.get("lng"),
                "Drop Lat": drop.get("lat"),
                "Drop Lng": drop.get("lng"),
            }
            st.json(passenger_info)

        # --- Estimated Trip Details Table ---
        st.header("Estimated Trip Details")
        if trip_fare_event:
            fare_list = safe_get(trip_fare_event, "body", "fare_details", default=[])
            estimated_fares = []
            for f in fare_list:
                est = safe_get(f, "estimated_fare", "fare_info", default={})
                fare_info = {
                    "Currency": f.get("currency_code", ""),
                    "Distance (km)": f.get("distance", ""),
                    "Duration (sec)": f.get("duration", ""),
                    "Base Fare": est.get("min_fare"),
                    "Distance Fare": safe_get(est, "fare_breakdown", "distance_fare"),
                    "Duration Fare": safe_get(est, "fare_breakdown", "duration_fare"),
                    "Waiting Fare": est.get("waiting_fare"),
                    "Free Waiting Time": est.get("free_waiting_time"),
                    "Extra Ride Fare": est.get("extra_ride_fare"),
                    "Above KM Fare": est.get("above_km_fare"),
                    "Surcharge": safe_get(est, "surcharge"),
                    "Is Upfront": f.get("is_upfront"),
                    "Ride Hour Enabled": f.get("ride_hour_enabled")
                }
                estimated_fares.append(fare_info)
            if estimated_fares:
                st.dataframe(pd.DataFrame(estimated_fares))

        # --- Fare Price File Table ---
        st.header("Fare Price File")
        if trip_fare_event:
            price_file = safe_get(trip_fare_event, "body", "fare_details", 0, "price_file", default={})
            price_rows = []
            for key in ["additional_charge", "distance_fare", "waiting_fare"]:
                for item in price_file.get(key, []):
                    row = item.copy()
                    row["type"] = key
                    price_rows.append(row)
            if price_rows:
                st.table(pd.DataFrame(price_rows))
            else:
                st.info("No price file data available")

        # --- Actual Trip Details (Completed + Ended) ---
        st.header("Actual Trip Details")
        if trip_completed_event or trip_ended_event:
            completed = trip_completed_event["body"] if trip_completed_event else {}
            ended = trip_ended_event["body"] if trip_ended_event else {}

            meter_details = safe_get(ended, "meter_details", "travel_details", default={})
            travel_info = safe_get(ended, "travel_info", default={})
            trip_info = safe_get(completed, "trip", default={})

            actual = {
                "Driver ID": ended.get("driver_id", trip_info.get("driver_id")),
                "Passenger ID": trip_info.get("passenger_id"),
                "Currency": ended.get("currency_code", trip_info.get("currency_code")),
                "Pickup Address": safe_get(trip_info, "actual_pickup", "address"),
                "Drop Address": safe_get(trip_info, "actual_drop", "address"),
                "Distance Travelled (m)": meter_details.get("distance_travelled"),
                "Waiting Time (sec)": meter_details.get("waiting_time"),
                "Total Trip Cost": trip_info.get("trip_cost"),
                "Promotion Code": safe_get(trip_info, "promo_code"),
                "Tip": trip_info.get("total_tip"),
                "Payment Method": safe_get(trip_info, "payment", 0, "method"),
                "Actual Duration (sec)": travel_info.get("actual_duration"),
                "Estimated Distance": travel_info.get("estimated_distance"),
                "Lost Mileage": travel_info.get("estimated_lost_mileage")
            }
            st.json(actual)

        # --- Driver Events Timeline ---
        st.header("Driver Events Timeline")
        timeline_data = []
        for e in driver_events:
            timeline_data.append({
                "Timestamp": format_timestamp(e.get("created_at")),
                "Event Type": e.get("type"),
                "Driver ID": safe_get(e, "body", "driver_id"),
                "Distance": safe_get(e, "body", "distance"),
                "ETA": safe_get(e, "body", "eta"),
                "Location": safe_get(e, "body", "location", "address"),
                "Extra Info": e.get("body")
            })
        df_timeline = pd.DataFrame(timeline_data)
        if not df_timeline.empty:
            st.dataframe(df_timeline.sort_values("Timestamp"))

        # --- Map ---
        st.header("Trip Map")

        # Initialize map centered at pickup
        m = folium.Map(location=[pickup.get("lat", 0), pickup.get("lng", 0)], zoom_start=12)

        # Pickup & Drop markers
        folium.Marker(
            location=[pickup.get("lat"), pickup.get("lng")],
            popup=f"Pickup: {pickup.get('address')}",
            icon=folium.Icon(color='green')
        ).add_to(m)
        folium.Marker(
            location=[drop.get("lat"), drop.get("lng")],
            popup=f"Drop: {drop.get('address')}",
            icon=folium.Icon(color='red')
        ).add_to(m)

        # --- OSRM Route between Pickup & Drop ---
        try:
            import requests

            osrm_url = f"http://router.project-osrm.org/route/v1/driving/{pickup.get('lng')},{pickup.get('lat')};{drop.get('lng')},{drop.get('lat')}?overview=full&geometries=geojson"
            r = requests.get(osrm_url).json()
            route_coords = [(c[1], c[0]) for c in r["routes"][0]["geometry"]["coordinates"]]
            folium.PolyLine(route_coords, color="blue", weight=4, opacity=0.6, tooltip="Planned Route").add_to(m)
        except Exception as e:
            st.warning(f"Could not fetch route from OSRM: {e}")


        st_folium(m, width=800, height=500)
