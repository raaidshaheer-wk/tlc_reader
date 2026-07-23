"""
Entry point — orchestration only. No parsing logic, no business logic,
per the architecture in SRS.md §1. Just: get the file, call trip_builder,
hand the Trip object to presentation/.
"""
import streamlit as st

from ingestion.loader import load_events_from_upload, InvalidTripFileError
from parsing.trip_builder import build_trip
from presentation.passenger_view import render_overview
from presentation.fare_view import render_fare
from presentation.actual_outcome_view import render_actual_outcome
from presentation.bidding_view import render_dispatch
from presentation.timeline_view import render_timeline
from presentation.map_view import render_map
from presentation.raw_events_view import render_raw_events
from presentation.glossary_view import render_glossary

st.set_page_config(page_title="PickMe Trip Investigation Dashboard", layout="wide")
st.title("PickMe Trip Investigation Dashboard")

uploaded_file = st.sidebar.file_uploader("Upload Trip JSON File", type="json")
if uploaded_file:
    try:
        events = load_events_from_upload(uploaded_file)
        trip = build_trip(events, source_filename=uploaded_file.name)
    except InvalidTripFileError as e:
        st.error(f"Couldn't read this file as a trip log: {e}")
        st.stop()

    tabs = st.tabs([
        "Overview", "Fare", "Actual Outcome",
        "Dispatch & Bidding", "Timeline", "Map", "Raw Events (Ground Truth)", "Glossary"
    ])
    with tabs[0]:
        render_overview(trip)
    with tabs[1]:
        render_fare(trip)
    with tabs[2]:
        render_actual_outcome(trip)
    with tabs[3]:
        render_dispatch(trip)
    with tabs[4]:
        render_timeline(trip)
    with tabs[5]:
        render_map(trip)
    with tabs[6]:
        render_raw_events(trip)
    with tabs[7]:
        render_glossary()
else:
    st.info("Upload a trip JSON file to begin.")
    with st.expander("Glossary — event types & coded values reference"):
        render_glossary()
