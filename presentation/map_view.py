"""
Trip Map — ported directly from the original app.py's map logic, which was
already solid (graceful OSRM failure handling per NFR/BR-6). Only change:
reads from trip.raw_events / trip.stops instead of module-level variables.
"""
import folium
import requests
import streamlit as st
from streamlit_folium import st_folium
from utils.helpers import safe_get, format_timestamp


def render_map(trip):
    st.subheader("Trip Map")

    pickup = trip.stops.pickup
    drops = trip.stops.drops_planned
    if not pickup:
        st.info("No pickup location available — cannot render map.")
        return

    route_points = [(pickup.get("lat"), pickup.get("lng"))]
    for d in drops:
        route_points.append((d.get("lat"), d.get("lng")))

    m = folium.Map(location=[pickup.get("lat", 0), pickup.get("lng", 0)], zoom_start=12)

    folium.Marker(
        location=[pickup.get("lat"), pickup.get("lng")],
        popup=f"Pickup: {pickup.get('address')}",
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(m)

    for i, d in enumerate(drops, start=1):
        lat, lng, addr = d.get("lat"), d.get("lng"), d.get("address", "")
        if lat and lng:
            folium.Marker(
                location=[lat, lng],
                popup=f"Drop {i}: {addr}",
                icon=folium.DivIcon(html=f"""
                    <div style="background-color:red;color:white;border-radius:50%;
                    width:28px;height:28px;text-align:center;line-height:28px;font-weight:bold;">
                    {i}</div>"""),
            ).add_to(m)

    trip_started = next((e for e in trip.raw_events if e["type"] == "trip_started"), None)
    if trip_started:
        loc = safe_get(trip_started, "body", "location")
        if loc:
            folium.Marker(
                location=[loc["lat"], loc["lng"]],
                popup=f"Trip Started: {loc.get('address')}",
                icon=folium.Icon(color="blue", icon="flag", prefix="fa"),
            ).add_to(m)

    driver_arrived = next((e for e in trip.raw_events if e["type"] == "driver_arrived"), None)
    if driver_arrived:
        loc = safe_get(driver_arrived, "body", "location")
        if loc:
            folium.Marker(
                location=[loc["lat"], loc["lng"]],
                popup=f"Driver Arrived: {loc.get('address')}",
                icon=folium.Icon(color="orange", icon="car", prefix="fa"),
            ).add_to(m)

    for e in trip.raw_events:
        if e["type"] != "waypoint_status_updated":
            continue
        body = e["body"]
        loc = body.get("location", {})
        lat, lng = loc.get("lat"), loc.get("lng")
        if lat and lng:
            folium.Marker(
                location=[lat, lng],
                popup=f"Stop {body.get('index')} — {body.get('status')}\n{loc.get('address')}\n{format_timestamp(e['created_at'])}",
                icon=folium.Icon(color="purple", icon="map-marker", prefix="fa"),
            ).add_to(m)

    trip_end_notif = next((e for e in trip.raw_events if e["type"] == "trip_end_notification"), None)
    if trip_end_notif:
        loc = safe_get(trip_end_notif, "body", "location")
        if loc:
            folium.Marker(
                location=[loc["lat"], loc["lng"]],
                popup=f"End Notification: {loc.get('address')}",
                icon=folium.Icon(color="red", icon="bell", prefix="fa"),
            ).add_to(m)

    driver_events = [e for e in trip.raw_events if e["type"] == "trip_accepted"]
    for i, event in enumerate(driver_events):
        loc = event["body"].get("location")
        if loc and loc.get("lat") and loc.get("lng"):
            is_real_driver = event["body"].get("driver_id") == trip.dispatch.real_driver_id
            color = "darkblue" if is_real_driver else "black"
            popup = f"Driver {event['body'].get('driver_id')} accepted"
            if not is_real_driver:
                popup += " (did not complete the trip)"
            folium.Marker(
                location=[loc["lat"], loc["lng"]],
                popup=popup,
                icon=folium.Icon(color=color, icon="car", prefix="fa"),
            ).add_to(m)

    try:
        coords = ";".join(f"{lng},{lat}" for lat, lng in route_points if lat and lng)
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"
        r = requests.get(osrm_url, timeout=10).json()
        route_coords = [(c[1], c[0]) for c in r["routes"][0]["geometry"]["coordinates"]]
        folium.PolyLine(route_coords, weight=4, opacity=0.7, tooltip="Planned Route").add_to(m)
    except Exception as e:
        st.warning(f"Could not fetch route from OSRM: {e}")

    legend_html = """
    <div style="position:fixed;bottom:100px;left:50px;width:230px;background-color:white;
    color:black;border:2px solid grey;z-index:9999;font-size:13px;padding:10px;">
    <b>Legend</b><br>
    <span style="color:green;">&#9679;</span> Pickup<br>
    <span style="color:red;">&#9679;</span> Drops<br>
    <span style="color:blue;">&#9679;</span> Trip Start<br>
    <span style="color:orange;">&#9679;</span> Driver Arrived<br>
    <span style="color:purple;">&#9679;</span> Waypoint Arrivals<br>
    <span style="color:red;">&#9679;</span> End Notification<br>
    <span style="color:darkblue;">&#9679;</span> Driver who completed trip<br>
    <span style="color:black;">&#9679;</span> Driver who cancelled/lost dispatch
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    st_folium(m, width=800, height=500, key=f"map_{trip.trip_id}")
