import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime, timezone
import json
import requests
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Trip Dashboard", layout="wide")
st.title("PickMe Trip Dashboard")

# --- Helper Functions ---
def safe_get(d, *keys, default=None):
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
        if ts > 1e12:
            ts = ts / 1000
        utc_time = datetime.fromtimestamp(ts, timezone.utc)
        sl_time = utc_time.astimezone(ZoneInfo("Asia/Colombo"))
        return sl_time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts

def ts_to_seconds(ts):
    """Convert ms timestamp to seconds"""
    return ts / 1000 if ts and ts > 1e12 else ts

def seconds_diff(ts1, ts2):
    """Return difference in seconds between two ms timestamps"""
    try:
        return int(abs(ts_to_seconds(ts1) - ts_to_seconds(ts2)))
    except Exception:
        return None

# --- User Input ---
uploaded_file = st.file_uploader("Upload Trip JSON File", type="json")
if uploaded_file:
    try:
        events = json.load(uploaded_file)

        # --- Separate events by type ---
        trip_created_event       = next((e for e in events if e["type"] == "trip_created"), None)
        trip_fare_event          = next((e for e in events if e["type"] == "trip_fare_updated"), None)
        trip_completed_event     = next((e for e in events if e["type"] == "trip_completed"), None)
        trip_ended_event         = next((e for e in events if e["type"] == "trip_ended"), None)
        trip_accepted_event      = next((e for e in events if e["type"] == "trip_accepted"), None)
        driver_arrived_event     = next((e for e in events if e["type"] == "driver_arrived"), None)
        trip_started_event       = next((e for e in events if e["type"] == "trip_started"), None)
        trip_end_notif_event     = next((e for e in events if e["type"] == "trip_end_notification"), None)
        waypoint_events          = [e for e in events if e["type"] == "waypoint_status_updated"]
        trip_received_events     = [e for e in events if e["type"] == "trip_received_by_driver"]
        trip_rejected_events     = [e for e in events if e["type"] == "trip_rejected_by_driver"]

        # --- Passenger & Trip Info ---
        st.header("Passenger & Trip Info")
        if trip_created_event:
            body = trip_created_event["body"]
            pickups = safe_get(body, "pickup", "location", default=[])
            drops = safe_get(body, "drop", "location", default=[])

            # Use trip_updated drop_locations if available — it contains the full
            # final list of stops including any mid-trip additions
            trip_updated_event = next((e for e in events if e["type"] == "trip_updated"), None)
            if trip_updated_event:
                updated_drops_raw = safe_get(trip_updated_event, "body", "drop_locations", default=[])
                if updated_drops_raw:
                    # trip_updated uses drop_locations (list of dicts with address/lat/lng)
                    drops = updated_drops_raw

            passenger_info = {
                "Passenger ID": safe_get(body, "passenger", "id"),
                "PIN": safe_get(body, "pin"),
                "Seats": safe_get(body, "seat_requirement"),
                "Pre-booking": safe_get(body, "pre_booking"),
                "Service Group": safe_get(body, "service_group_code"),
                "Number of Pickups": len(pickups),
                "Number of Drops (final)": len(drops),
            }
            st.json(passenger_info)

            if pickups:
                st.subheader("Pickup Locations")
                st.dataframe(pd.DataFrame(pickups).astype(str))

            if drops:
                st.subheader("Drop Locations (Stops)")
                if trip_updated_event:
                    st.caption("ℹ️ Stop list reflects mid-trip updates from `trip_updated` event.")

                # Build waypoint lookup: waypoint index 1 = stop 1, 2 = stop 2, etc.
                waypoint_by_index = {
                    e["body"].get("index"): e
                    for e in events if e["type"] == "waypoint_status_updated"
                }
                enriched_drops = []
                for i, d in enumerate(drops, start=1):
                    wp = waypoint_by_index.get(i)
                    wp_body = wp["body"] if wp else {}
                    wp_loc = wp_body.get("location", {})
                    # Final stop uses trip_ended location instead of a waypoint
                    is_final = (i == len(drops))
                    if is_final and trip_ended_event:
                        ended_loc = safe_get(trip_ended_event, "body", "location", default={})
                        actual_address = ended_loc.get("address", "-")
                        actual_lat = ended_loc.get("lat", "-")
                        actual_lng = ended_loc.get("lng", "-")
                        arrival_status = "COMPLETED"
                        arrival_time = format_timestamp(trip_ended_event["created_at"])
                    else:
                        actual_address = wp_loc.get("address", "-") if wp else "-"
                        actual_lat = wp_loc.get("lat", "-") if wp else "-"
                        actual_lng = wp_loc.get("lng", "-") if wp else "-"
                        arrival_status = wp_body.get("status", "-") if wp else "-"
                        arrival_time = format_timestamp(wp["created_at"]) if wp else "-"

                    enriched_drops.append({
                        "Stop #": i,
                        "Planned Address": d.get("address", ""),
                        "Planned Lat": d.get("lat"),
                        "Planned Lng": d.get("lng"),
                        "Actual Address": actual_address,
                        "Actual Lat": actual_lat,
                        "Actual Lng": actual_lng,
                        "Arrival Status": arrival_status,
                        "Arrival Time": arrival_time,
                    })
                st.dataframe(pd.DataFrame(enriched_drops).astype(str))

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
                for meta in safe_get(e, "body", "business_metadata", default=[]):
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
            st.dataframe(pd.DataFrame(ride_trip_rows).astype(str))
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
                    df = df[cols_to_show].rename(columns={
                        "id": "ID", "name": "Name", "amount": "Amount(LKR)", "type": "Type",
                        "base_fare": "Base Fare(LKR)", "distance": "Distance(km)", "km_fare": "KM Fare",
                        "end_time": "End Time(s)", "fare": "Fare(LKR)"
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

            # Compute wait times from newly used events
            passenger_wait_time = None
            driver_wait_time = None
            end_notif_to_ended_gap = None

            if trip_accepted_event and trip_started_event:
                passenger_wait_time = seconds_diff(
                    trip_started_event["created_at"],
                    trip_accepted_event["created_at"]
                )

            if driver_arrived_event and trip_started_event:
                driver_wait_time = seconds_diff(
                    trip_started_event["created_at"],
                    driver_arrived_event["created_at"]
                )

            if trip_end_notif_event and trip_ended_event:
                end_notif_to_ended_gap = seconds_diff(
                    trip_ended_event["created_at"],
                    trip_end_notif_event["created_at"]
                )

            actual = {
                "Driver ID": ended.get("driver_id", trip_info.get("driver_id")),
                "Passenger ID": trip_info.get("passenger_id"),
                "Currency": ended.get("currency_code", trip_info.get("currency_code")),
                "Pickup Address": safe_get(trip_info, "actual_pickup", "address"),
                "Drop Address": safe_get(trip_info, "actual_drop", "address"),
                "Trip Start Time": format_timestamp(trip_started_event["created_at"]) if trip_started_event else None,
                "Driver Arrived Time": format_timestamp(driver_arrived_event["created_at"]) if driver_arrived_event else None,
                "Trip End Notification Time": format_timestamp(trip_end_notif_event["created_at"]) if trip_end_notif_event else None,
                "Passenger Wait Time (sec)": passenger_wait_time,
                "Driver Wait Time at Pickup (sec)": driver_wait_time,
                "End Notification to Fare Finalization Gap (sec)": end_notif_to_ended_gap,
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

        # --- Per-Stop Breakdown (waypoint_status_updated) ---
        st.header("Per-Stop Breakdown")
        if waypoint_events:
            waypoint_rows = []
            for e in sorted(waypoint_events, key=lambda x: x["body"].get("index", 0)):
                body = e["body"]
                waypoint_rows.append({
                    "Stop Index": body.get("index"),
                    "Status": body.get("status"),
                    "Address": safe_get(body, "location", "address"),
                    "Lat": safe_get(body, "location", "lat"),
                    "Lng": safe_get(body, "location", "lng"),
                    "Arrival Time": format_timestamp(e["created_at"])
                })
            st.dataframe(pd.DataFrame(waypoint_rows).astype(str))
        else:
            st.info("No waypoint data available")

        # --- Trip Bidding Details ---
        st.header("Trip Bidding Details")
        received_driver_ids = {e["body"].get("driver_id") for e in trip_received_events}
        rejected_driver_map = {
            e["body"].get("driver_id"): e["body"].get("rejection_type", "")
            for e in trip_rejected_events
        }

        bidding_rows = []
        for e in events:
            body = e.get("body", {})
            trip_id = body.get("trip_id")
            if e["type"] in ["driver_selected", "driver_assigned"]:
                for d in body.get("drivers", []):
                    driver_id = d.get("driver_id")
                    bidding_rows.append({
                        "Trip ID": str(trip_id),
                        "Driver ID": str(driver_id),
                        "Bidding?": str(d.get("bidding", False)),
                        "Bid Amount": pd.to_numeric(None),
                        "Assigned?": e["type"] == "driver_assigned",
                        "Winner?": False,
                        "Received Trip?": driver_id in received_driver_ids,
                        "Rejection Type": rejected_driver_map.get(driver_id, "-"),
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
            st.dataframe(pd.DataFrame(bidding_rows))

        # --- Complete Trip Events Timeline (ALL event types) ---
        st.header("Complete Trip Events Timeline")
        event_extra_info = {
            "trip_created":             lambda b: f"Passenger: {safe_get(b,'passenger','id')} | PIN: {b.get('pin')}",
            "trip_fare_updated":        lambda b: f"Fare: {safe_get(b,'fare_details',0,'estimated_fare','fare_info','min_fare')} {safe_get(b,'fare_details',0,'currency_code')} | Dist: {safe_get(b,'fare_details',0,'distance')}km",
            "driver_selected":          lambda b: f"Drivers considered: {len(b.get('drivers', []))}",
            "driver_assigned":          lambda b: f"Assigned Driver: {b.get('driver_id')} | ETA: {b.get('eta')}s | Blast: {b.get('blast_dispatch')}",
            "trip_received_by_driver":  lambda b: f"Driver {b.get('driver_id')} received the trip",
            "trip_accepted":            lambda b: f"Driver {b.get('driver_id')} accepted at {safe_get(b,'location','address')}",
            "trip_rejected_by_driver":  lambda b: f"Driver {b.get('driver_id')} rejected — Reason: {b.get('rejection_type')}",
            "driver_arrived":           lambda b: f"Driver {b.get('driver_id')} arrived at {safe_get(b,'location','address')}",
            "trip_updated":             lambda b: f"Update type: {b.get('update_type')} | Stops: {len(b.get('drop_locations', []))}",
            "trip_started":             lambda b: f"Driver {b.get('driver_id')} started at {safe_get(b,'location','address')}",
            "waypoint_status_updated":  lambda b: f"Stop {b.get('index')} — {b.get('status')} at {safe_get(b,'location','address')}",
            "trip_end_notification":    lambda b: f"Driver {b.get('driver_id')} near end at {safe_get(b,'location','address')}",
            "trip_ended":               lambda b: f"Fare: {safe_get(b,'final_trip_fare','final_trip_fare')} | Dist: {safe_get(b,'meter_details','travel_details','distance_travelled')}m | Duration: {safe_get(b,'travel_info','actual_duration')}s",
            "trip_completed":           lambda b: f"Cost: {safe_get(b,'trip','trip_cost')} | Surge: {safe_get(b,'surge','value')} | Payment: {safe_get(b,'trip','payment',0,'method')}",
        }

        timeline_data = []
        for e in events:
            body = e.get("body", {})
            event_type = e.get("type", "")
            try:
                extra = event_extra_info.get(event_type, lambda b: "")(body)
            except Exception:
                extra = ""

            timeline_data.append({
                "Timestamp": str(format_timestamp(e.get("created_at"))),
                "Event Type": event_type,
                "Category": (
                    "Driver Event" if event_type in [
                        "driver_selected", "driver_assigned", "trip_received_by_driver",
                        "trip_accepted", "trip_rejected_by_driver", "driver_arrived"
                    ] else
                    "Waypoint Event" if event_type == "waypoint_status_updated" else
                    "Fare Event" if event_type in ["trip_fare_updated"] else
                    "Trip Event"
                ),
                "Driver ID": str(safe_get(body, "driver_id", default="-")),
                "Location": str(safe_get(body, "location", "address", default="-")),
                "Summary": extra,
                "Extra Info": json.dumps(body, indent=2, ensure_ascii=False)
            })

        df_timeline = pd.DataFrame(timeline_data)
        if not df_timeline.empty:
            df_timeline.sort_values("Timestamp", inplace=True)
            st.dataframe(df_timeline, use_container_width=True)

            st.subheader("Event Body Inspector")
            sorted_events = sorted(events, key=lambda e: e.get("created_at", 0))
            for e in sorted_events:
                event_type = e.get("type", "unknown")
                ts = format_timestamp(e.get("created_at", 0))
                with st.expander(f"🔍  [{ts}]  {event_type}"):
                    st.json(e.get("body", {}))

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
            lat, lng, addr = d.get("lat"), d.get("lng"), d.get("address", "")
            if lat and lng:
                folium.Marker(
                    location=[lat, lng],
                    popup=f"Drop {i}: {addr}",
                    icon=folium.DivIcon(html=f"""
                        <div style="background-color:red;color:white;border-radius:50%;
                        width:28px;height:28px;text-align:center;line-height:28px;font-weight:bold;">
                        {i}</div>""")
                ).add_to(m)

        # Trip start location marker
        if trip_started_event:
            loc = safe_get(trip_started_event, "body", "location")
            if loc:
                folium.Marker(
                    location=[loc["lat"], loc["lng"]],
                    popup=f"Trip Started: {loc.get('address')}",
                    icon=folium.Icon(color='blue', icon='flag', prefix='fa')
                ).add_to(m)

        # Driver arrived marker
        if driver_arrived_event:
            loc = safe_get(driver_arrived_event, "body", "location")
            if loc:
                folium.Marker(
                    location=[loc["lat"], loc["lng"]],
                    popup=f"Driver Arrived: {loc.get('address')}",
                    icon=folium.Icon(color='orange', icon='car', prefix='fa')
                ).add_to(m)

        # Waypoint arrival markers
        for e in waypoint_events:
            body = e["body"]
            loc = body.get("location", {})
            lat, lng = loc.get("lat"), loc.get("lng")
            if lat and lng:
                folium.Marker(
                    location=[lat, lng],
                    popup=f"Stop {body.get('index')} — {body.get('status')}\n{loc.get('address')}\n{format_timestamp(e['created_at'])}",
                    icon=folium.Icon(color='purple', icon='map-marker', prefix='fa')
                ).add_to(m)

        # Trip end notification marker
        if trip_end_notif_event:
            loc = safe_get(trip_end_notif_event, "body", "location")
            if loc:
                folium.Marker(
                    location=[loc["lat"], loc["lng"]],
                    popup=f"End Notification: {loc.get('address')}",
                    icon=folium.Icon(color='red', icon='bell', prefix='fa')
                ).add_to(m)

        # Driver accepted location markers
        driver_events = [e for e in events if e["type"] == "trip_accepted"]
        for idx, event in enumerate(driver_events):
            loc = event["body"].get("location")
            if loc and loc.get("lat") and loc.get("lng"):
                color = "darkblue" if idx == len(driver_events) - 1 else "black"
                folium.Marker(
                    location=[loc["lat"], loc["lng"]],
                    popup=f"Driver {event['body'].get('driver_id')} accepted",
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
        <div style="position:fixed;bottom:100px;left:50px;width:220px;background-color:white;
        color:black;border:2px solid grey;z-index:9999;font-size:13px;padding:10px;">
        <b>Legend</b><br>
        <span style="color:green;">&#9679;</span> Pickup<br>
        <span style="color:red;">&#9679;</span> Drops<br>
        <span style="color:blue;">&#9679;</span> Trip Start<br>
        <span style="color:orange;">&#9679;</span> Driver Arrived<br>
        <span style="color:purple;">&#9679;</span> Waypoint Arrivals<br>
        <span style="color:red;">&#9679;</span> End Notification<br>
        <span style="color:darkblue;">&#9679;</span> Driver (accepted)
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
        st_folium(m, width=800, height=500)

    except Exception as e:
        st.error(f"Failed to read JSON file: {e}")