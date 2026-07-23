"""
Resolved glossary constants from the official TLC (Trip Life Cycle) glossary.

Why this file exists: raw event JSON is full of small integers (module=5,
selection_type=13, vehicle_type=2...) that mean nothing to a support agent
looking at a screen. Every one of these should be resolved to a label before
it reaches presentation/ — that's SR-5 in the SRS. Centralizing them here
means when a new code shows up in a future trip sample, there's exactly one
place to add it (satisfies BR-7: one new event/field type, one place to touch).

Every dict has a `.get(code, f"Unknown (code: {code})")` pattern via
`resolve()` below, so an unmapped code never crashes the page (NFR-4) — it
just shows up clearly as unknown, which is itself useful signal that
trip_info.md needs updating with a new sample.
"""

BOOKED_BY = {
    1: "Passenger",
    2: "Operator",
}

BOOKING_FROM = {
    0: "Web",
    1: "Device",
    2: "Road Pick Up",
    3: "Dispatcher",
    4: "Corporate",
    5: "Kiosk",
    6: "Commute",
}

MODULE = {
    1: "Passenger",
    2: "Road Pickup",
    3: "Dispatcher",
    4: "Corporate",
    5: "Food / Marketplace",
    6: "Commute",
    7: "Auto Dispatcher",
}

PAYMENT_METHOD = {
    1: "Cash",
    2: "Non-cash",
    3: "Points",
    5: "IPAY",
    6: "UPAY",
    7: "FRIMI",
    8: "Touch",
    9: "Alipay",
    10: "GENIE",
    11: "Pay by QR",
    12: "FLASH",
    13: "LANKAQR",
    14: "LANKAQR / UPI / Alipay",
    15: "CASA",
    16: "eSewa",
}

VEHICLE_TYPE = {
    1: "Tuk", 2: "Mini", 3: "Car", 4: "Flex", 10: "Van", 18: "Bike",
    19: "Tuk H", 24: "Minivan", 29: "Light Open", 34: "Light",
    38: "Mover Open", 42: "Mover", 43: "Food", 47: "Shuttle", 49: "Flash",
    50: "Food Pickup", 51: "Food Pool", 52: "Food Plus", 54: "Food Maldives",
    55: "Food Premium", 56: "Food Exclusive", 59: "Flash L", 65: "Food H",
    66: "Flash XL", 67: "Gas Delivery", 68: "Grocery Pool",
    69: "Grocery Regular", 70: "Market Pool", 71: "Market Delivery",
    72: "Maldives Market", 73: "Commute 5x", 74: "Santa2021",
    75: "Commute 10x", 77: "Flash XXL", 78: "LMP Delivery",
    79: "Carrier 20ft", 80: "Carrier 40ft", 81: "Share", 83: "Bicycle",
    85: "EV", 86: "NPTA TUK", 88: "Utra", 89: "Mover Plus",
    90: "Mover Plus (variant)", 92: "Delivery - Own Fleet", 102: "Mover XL",
}

ASSIGN_TYPE = {
    0: "Normal",
    -1: "Dispatcher portal",
}

SELECTION_TYPE = {
    0: "Normal", 2: "Road Pickup", 3: "DH", 6: "FH", 7: "FH + DH",
    8: "MB", 9: "DH + MB", 10: "Trip Scanner + DH + MB",
    11: "Trip Scanner + MB", 12: "Trip Scanner + DH", 13: "Trip Scanner",
    14: "Trip Scanner + Bidding", 15: "Trip Scanner + Bidding + MB",
    16: "Trip Scanner + Bidding + DH",
    17: "Trip Scanner + Bidding + DH + MB",
}

# NOTE: this is the glossary's `acceptType`, mapped to the `trip_accept_type`
# field we see in `trip_accepted` events.
TRIP_ACCEPT_TYPE = {
    0: "Default",
    1: "Driver (automatch)",
    2: "Passenger (accepted a bid)",
}

CANCELLED_FROM = {
    1: "Passenger", 2: "Driver", 3: "Dispatcher", 4: "Corporate",
    5: "Auto", 6: "Console",
}

CANCEL_TYPE = {
    1: "Before accept",
    2: "After accept",
}

TRIP_STATUS = {
    1: "Driver Assigned",
    2: "Driver Accepted",
    3: "Trip Started",
}

BOOKING_STATUS = {
    1: "Trip Assigned",
    2: "Trip Accepted",
    3: "Trip Started",
    4: "Trip Cancelled",
    5: "Trip Completed",
}

TRAVEL_STATUS = {
    0: "Not Completed", 1: "Completed", 2: "In Progress",
    3: "Arrived", 4: "Cancelled by Passenger", 5: "Waiting for Payment",
    6: "Missed", 7: "Dispatched", 8: "Cancelled", 9: "Confirmed",
    10: "Reassign", 11: "Rejected", 12: "Unavailable",
}

LOYALTY_TIER = {
    1: "Elite", 2: "Platinum", 3: "Gold", 4: "Cabbie", 5: "Silver", 6: "Bronze",
}


def resolve(table: dict, code, prefix: str = "") -> str:
    """
    Look up `code` in `table`, returning a readable label. Falls back to
    "Unknown (code: N)" instead of raising, so one unrecognized code (a new
    vehicle type, a new selection_type) never crashes a page — it just
    surfaces as a visible gap, which is a signal to update this file.
    """
    if code is None:
        return "-"
    label = table.get(code)
    if label is None:
        return f"Unknown (code: {code})"
    return f"{prefix}{label}" if prefix else label
