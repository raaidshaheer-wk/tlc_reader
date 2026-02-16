import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import json
import requests

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
uploaded_file = st.file_uploader("Upload Trip JSON File", type="json")
if uploaded_file:
    try:
        events = json.load(uploaded_file)

        # --- Separate events by type ---
        trip_created_event = next((e for e in events if e["type"] == "trip_created"), None)
        trip_fare_event = next((e for e in events if e["type"] == "trip_fare_updated"), None)
        trip_completed_event = next((e for e in events if e["type"] == "trip_completed"), None)
        trip_ended_event = next((e for e in events if e["type"] == "trip_ended"), None)

        # --- Passenger & Trip Info ---
        st.header("Passenger & Trip Info")
        if trip_created_event:
            body = trip_created_event["body"]
            pickups = safe_get(body, "pickup", "location", default=[])
            drops = safe_get(body, "drop", "location", default=[])

            passenger_info = {
                "Passenger ID": safe_get(body, "passenger", "id"),
                "PIN": safe_get(body, "pin"),
                "Seats": safe_get(body, "seat_requirement"),
                "Pre-booking": safe_get(body, "pre_booking"),
                "Service Group": safe_get(body, "service_group_code"),
                "Number of Pickups": len(pickups),
                "Number of Drops": len(drops),
            }
            st.json(passenger_info)

            if pickups:
                st.subheader("Pickup Locations")
                df_pickups = pd.DataFrame(pickups)
                st.dataframe(df_pickups.astype(str))  # Convert all to string

            if drops:
                st.subheader("Drop Locations (Stops)")
                df_drops = pd.DataFrame(drops)
                st.dataframe(df_drops.astype(str))  # Convert all to string

            # Keep first pickup & last drop
            pickup = pickups[0] if pickups else {}
            drop = drops[-1] if drops else {}

        # --- Ride & Trip Overview ---
        st.header("Ride & Trip Overview")
        ride_trip_rows = []
        for e in events:
            trip_id = safe_get(e, "body", "trip_id")
            if trip_id is not None:
                driver_id = safe_get(e, "body", "driver_id")
                ride_id = None
                business_metadata = safe_get(e, "body", "business_metadata", default=[])
                for meta in business_metadata:
                    if meta.get("key") == "ride_id":
                        ride_id = meta.get("value")
                        break
                ride_trip_rows.append({
                    "Ride ID": str(ride_id),
                    "Trip ID": str(trip_id),
                    "Event": str(e.get("type")),
                    "Driver ID": str(driver_id)
                })

        if ride_trip_rows:
            df_ride_trip = pd.DataFrame(ride_trip_rows)
            st.dataframe(df_ride_trip.astype(str))
        else:
            st.info("No ride/trip data available")

        # --- Estimated Trip Details ---
        st.header("Estimated Trip Details")
        if trip_fare_event:
            fare_list = safe_get(trip_fare_event, "body", "fare_details", default=[])
            estimated_fares = []
            for f in fare_list:
                est = safe_get(f, "estimated_fare", "fare_info", default={})
                fare_info = {
                    "Currency": str(f.get("currency_code", "")),
                    "Total Distance (km)": pd.to_numeric(f.get("distance", 0), errors='coerce'),
                    "Total Duration (sec)": pd.to_numeric(f.get("duration", 0), errors='coerce'),
                    "Number of Stops": len(drops),
                    "Base Fare": pd.to_numeric(est.get("min_fare", 0), errors='coerce'),
                    "Distance Fare": str(safe_get(est, "fare_breakdown", "distance_fare")),
                    "Duration Fare": str(safe_get(est, "fare_breakdown", "duration_fare")),
                    "Waiting Fare": str(est.get("waiting_fare")),
                    "Free Waiting Time": pd.to_numeric(est.get("free_waiting_time", 0), errors='coerce'),
                    "Extra Ride Fare": pd.to_numeric(est.get("extra_ride_fare", 0), errors='coerce'),
                    "Above KM Fare": pd.to_numeric(est.get("above_km_fare", 0), errors='coerce'),
                    "Is Upfront": str(f.get("is_upfront")),
                    "Ride Hour Enabled": str(f.get("ride_hour_enabled"))
                }
                estimated_fares.append(fare_info)
            if estimated_fares:
                st.dataframe(pd.DataFrame(estimated_fares))

                # --- Fare Price File Tables ---
            st.header("Fare Price File")
            if trip_fare_event:
                price_file = safe_get(trip_fare_event, "body", "fare_details", 0, "price_file", default={})

                table_columns = {
                    "additional_charge": ["id", "name", "amount", "type"],
                    "distance_fare": ["base_fare", "distance", "km_fare"],
                    "waiting_fare": ["end_time", "fare"]
                }

                for key in ["additional_charge", "distance_fare", "waiting_fare"]:
                    items = price_file.get(key, [])
                    if items:
                        st.subheader(key.replace("_", " ").title())
                        df = pd.DataFrame(items)

                        cols_to_show = [col for col in table_columns[key] if col in df.columns]
                        df = df[cols_to_show]

                        df = df.rename(columns={
                            "id": "ID",
                            "name": "Name",
                            "amount": "Amount",
                            "type": "Type",
                            "base_fare": "Base Fare",
                            "distance": "Distance",
                            "km_fare": "KM Fare",
                            "end_time": "End Time",
                            "fare": "Fare"
                        })
                        st.table(df)
                    else:
                        st.info(f"No {key.replace('_', ' ')} data available")

            # --- Actual Trip Details ---
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

        # --- Trip Bidding Details ---
        st.header("Trip Bidding Details")
        bidding_rows = []
        for e in events:
            body = e.get("body", {})
            trip_id = body.get("trip_id")
            if e["type"] in ["driver_selected", "driver_assigned"]:
                drivers = body.get("drivers", [])
                for d in drivers:
                    driver_id = d.get("driver_id")
                    bidding_rows.append({
                        "Trip ID": str(trip_id),
                        "Driver ID": str(driver_id),
                        "Bidding?": str(d.get("bidding", False)),
                        "Bid Amount": pd.to_numeric(None),
                        "Assigned?": e["type"] == "driver_assigned",
                        "Winner?": False,
                        "Selection Type": str(d.get("selection_type")),
                        "ETA (s)": pd.to_numeric(d.get("eta", 0), errors='coerce'),
                        "Distance (m)": pd.to_numeric(d.get("distance", 0), errors='coerce')
                    })

        for e in events:
            if e["type"] == "trip_accepted":
                body = e.get("body", {})
                trip_id = body.get("trip_id")
                driver_id = body.get("driver_id")
                bid_amount = body.get("bid_amount")
                for row in bidding_rows:
                    if row["Trip ID"] == str(trip_id) and row["Driver ID"] == str(driver_id):
                        row["Bid Amount"] = pd.to_numeric(bid_amount, errors='coerce')
                        row["Winner?"] = True

        if bidding_rows:
            df_bidding = pd.DataFrame(bidding_rows)
            st.dataframe(df_bidding)

        # --- Timeline ---
        st.header("Complete Trip Events Timeline")
        timeline_data = []
        for e in events:
            body = e.get("body", {})
            timeline_data.append({
                "Timestamp": str(format_timestamp(e.get("created_at"))),
                "Event Type": str(e.get("type")),
                "Category": "Driver Event" if "driver_id" in body or "drivers" in body else "Trip Event",
                "Driver ID": str(safe_get(body, "driver_id", default="-")),
                "Distance": pd.to_numeric(safe_get(body, "distance", default=0), errors='coerce'),
                "ETA": pd.to_numeric(safe_get(body, "eta", default=0), errors='coerce'),
                "Location": str(safe_get(body, "location", "address", default="-")),
                "Extra Info": str(body)
            })

        df_timeline = pd.DataFrame(timeline_data)
        if not df_timeline.empty:
            df_timeline.sort_values("Timestamp", inplace=True)
            st.dataframe(df_timeline)

        # --- Trip Map ---
        st.header("Trip Map")
        route_points = []
        if pickup:
            route_points.append((pickup.get("lat"), pickup.get("lng")))
        for d in drops:
            route_points.append((d.get("lat"), d.get("lng")))

        m = folium.Map(location=[pickup.get("lat", 0), pickup.get("lng", 0)], zoom_start=12)

        # Pickup marker
        folium.Marker(
            location=[pickup.get("lat"), pickup.get("lng")],
            popup=f"Pickup: {pickup.get('address')}",
            icon=folium.Icon(color='green', icon='play')
        ).add_to(m)

        # Drop markers
        for i, d in enumerate(drops, start=1):
            lat = d.get("lat")
            lng = d.get("lng")
            addr = d.get("address", "")
            if lat and lng:
                folium.Marker(
                    location=[lat, lng],
                    popup=f"Drop {i}: {addr}",
                    icon=folium.DivIcon(html=f"""
                        <div style="
                        background-color:red;
                        color:white;
                        border-radius:50%;
                        width:28px;
                        height:28px;
                        text-align:center;
                        line-height:28px;
                        font-weight:bold;">
                        {i}
                        </div>""")
                ).add_to(m)

        # Driver markers

        driver_events = [e for e in events if e["type"] == "trip_accepted"]
        for idx, event in enumerate(driver_events):
            loc = event["body"].get("location")
            if loc and loc.get("lat") and loc.get("lng"):
                # Use black for previous drivers, lightgreen for final
                color = "darkblue" if idx == len(driver_events) - 1 else "black"
                folium.Marker(
                    location=[loc["lat"], loc["lng"]],
                    popup=f"Driver {event['body'].get('driver_id')}",
                    icon=folium.Icon(color=color, icon='car', prefix='fa')
                ).add_to(m)

        # OSRM route
        try:
            coords = ";".join([f"{lng},{lat}" for lat, lng in route_points])
            osrm_url = f"http://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"
            r = requests.get(osrm_url).json()
            route_coords = [(c[1], c[0]) for c in r["routes"][0]["geometry"]["coordinates"]]
            folium.PolyLine(route_coords, weight=4, opacity=0.7, tooltip="Planned Route").add_to(m)
        except Exception as e:
            st.warning(f"Could not fetch route from OSRM: {e}")

        # Legend
        legend_html = """
        <div style="
        position: fixed;
        bottom: 100px;
        left: 50px;
        width: 150px;
        height: 120px;
        background-color:white;
        color: black;
        border:2px solid grey;
        z-index:9999;
        font-size:14px;
        padding:10px;">
        <b>Legend</b><br>
        <span style="color:green;">&#9679;</span> Pickup<br>
        <span style="color:red;">&#9679;</span> Drops<br>
        <span style="color:black;">&#9679;</span> Driver (previous)<br>
        <span style="color:yellow;">&#9679;</span> Driver (final)
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        st_folium(m, width=800, height=500)

    except Exception as e:
        st.error(f"Failed to read JSON file: {e}")
