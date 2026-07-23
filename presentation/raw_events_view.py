"""
The ground-truth viewer (Rules.md #11/#12). Every computed value shown
elsewhere in the app traces back to one or more raw events - this view lets
an investigator check the actual source instead of trusting the calculation.

Organized, not dumped: events are grouped by type, then shown in
chronological order within each group, each pretty-printed individually -
not one giant st.json() of the whole 500-line array, which is unreadable.
"""
import json
import streamlit as st
from utils.helpers import format_timestamp


def render_raw_events(trip):
    st.subheader("Raw Event Log — Ground Truth")
    st.caption(
        "Every number and label elsewhere in this app is *computed* from "
        "these events. If something here looks different from a calculated "
        "value shown elsewhere, trust this — it means the calculation has "
        "a bug, not that the raw data is wrong."
    )

    events_by_type = {}
    for e in trip.raw_events:
        events_by_type.setdefault(e.get("type", "unknown"), []).append(e)

    # order groups by when each type first appears, so the log reads like
    # the actual story of the trip rather than an alphabetical dump
    ordered_types = sorted(
        events_by_type.keys(),
        key=lambda t: events_by_type[t][0].get("created_at", 0),
    )

    search = st.text_input(
        "Filter by event type or field value (optional)",
        key=f"raw_search_{trip.trip_id}",
    )

    for event_type in ordered_types:
        events = events_by_type[event_type]
        label = f"{event_type} ({len(events)})"
        if search and search.lower() not in event_type.lower() and not any(
            search.lower() in json.dumps(e["body"]).lower() for e in events
        ):
            continue

        with st.expander(label):
            for i, e in enumerate(events, start=1):
                if len(events) > 1:
                    st.markdown(f"**Occurrence {i} — {format_timestamp(e['created_at'])}**")
                else:
                    st.markdown(f"**{format_timestamp(e['created_at'])}**")
                st.json(e["body"])

    st.divider()
    st.download_button(
        "Download this trip's full raw JSON",
        data=json.dumps(trip.raw_events, indent=2),
        file_name=f"trip_{trip.trip_id}_raw.json",
        mime="application/json",
        key=f"raw_download_{trip.trip_id}",
    )
