"""
The "order coming in" layer: takes an uploaded Streamlit file, validates it's
a real trip event log, and returns a plain list of dicts. Nothing here knows
about Trip objects or Streamlit widgets beyond the file uploader itself -
that's cooking's and plating's job respectively.
"""
import json


class InvalidTripFileError(Exception):
    """Raised when an uploaded file isn't a usable trip event log."""


def load_events_from_upload(uploaded_file) -> list[dict]:
    """
    Parse an uploaded file into a list of raw event dicts.

    Why validate here and not later: catching a bad file at the point of
    upload gives a clear, immediate error message ("this isn't a trip log")
    instead of a confusing crash three modules deep in parsing/.
    """
    try:
        raw = json.loads(uploaded_file.read())
    except json.JSONDecodeError as e:
        raise InvalidTripFileError(f"Not valid JSON: {e}")

    if not isinstance(raw, list):
        raise InvalidTripFileError("Expected a JSON array of events.")

    if not raw:
        raise InvalidTripFileError("File contains an empty event list.")

    for e in raw:
        if not isinstance(e, dict) or "type" not in e or "body" not in e:
            raise InvalidTripFileError(
                "Expected each event to have at least 'type' and 'body' fields."
            )

    return raw
