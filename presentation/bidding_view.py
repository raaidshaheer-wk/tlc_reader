"""
Dispatch & Bidding — shows every round reconstructed by parsing/dispatch.py
(SR-2), plus the accept-then-cancel flag (SR-3) and a per-driver bidding
table (same shape as the original app, resolved through Trip.raw_events
since this is inherently an event-level view).
"""
import pandas as pd
import streamlit as st
from parsing.lookups import SELECTION_TYPE, resolve


def render_dispatch(trip):
    st.subheader("Dispatch Summary")
    d = trip.dispatch
    st.json({
        "Dispatch Rounds": len(d.rounds),
        "Total Driver Rejections": d.total_rejections,
        "Bidding Dispatch": d.bidding,
        "Blast Dispatch": d.blast_dispatch,
        "Driver Cancelled After Accepting": d.cancelled_after_accept,
        "Resolved Real Driver ID": d.real_driver_id,
    })

    if d.cancelled_after_accept:
        st.warning(
            "⚠️ At least one driver accepted this trip and then cancelled "
            "before it started. The rounds below show the full sequence."
        )

    st.subheader("Dispatch Rounds")
    round_rows = []
    for r in d.rounds:
        round_rows.append({
            "Round": r.round_number,
            "Candidates Considered": len(r.candidates),
            "Assigned Driver": r.assigned_driver_id,
            "Outcome": r.outcome,
        })
    if round_rows:
        st.dataframe(pd.DataFrame(round_rows), use_container_width=True)
    else:
        st.info("No dispatch round data available.")

    st.subheader("Per-Driver Bidding / Candidate Detail")
    received_ids = {
        e["body"].get("driver_id")
        for e in trip.raw_events if e["type"] == "trip_received_by_driver"
    }
    rejected_map = {
        e["body"].get("driver_id"): e["body"].get("rejection_type", "")
        for e in trip.raw_events if e["type"] == "trip_rejected_by_driver"
    }
    bid_amounts = {
        e["body"].get("driver_id"): e["body"].get("bid_amount")
        for e in trip.raw_events if e["type"] == "trip_accepted"
    }

    bidding_rows = []
    for e in trip.raw_events:
        if e["type"] in ("driver_selected", "driver_assigned"):
            for cand in e["body"].get("drivers", []):
                driver_id = cand.get("driver_id")
                bidding_rows.append({
                    "Driver ID": driver_id,
                    "Bidding?": cand.get("bidding", False),
                    "Bid Amount": bid_amounts.get(driver_id),
                    "Was Assigned?": e["type"] == "driver_assigned",
                    "Was Real Driver?": driver_id == d.real_driver_id,
                    "Received Trip?": driver_id in received_ids,
                    "Rejection Reason": rejected_map.get(driver_id, "-"),
                    "Selection Type": resolve(SELECTION_TYPE, cand.get("selection_type")),
                    "ETA (s)": cand.get("eta"),
                    "Distance (m)": cand.get("distance"),
                })
    if bidding_rows:
        st.dataframe(pd.DataFrame(bidding_rows), use_container_width=True)
    else:
        st.info("No dispatch/bidding candidate data available.")
