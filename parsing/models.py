"""
Data models — the contract between parsing/ ("cooking") and presentation/
("plating"). Every view in presentation/ should only ever need a Trip object,
never a raw event list.

Why dataclasses and not dicts: a dict typo (`trip["passneger_id"]`) fails
silently or with a confusing KeyError deep in a view function. A dataclass
typo (`trip.passneger_id`) is caught immediately by any editor/linter, and
it's self-documenting — anyone opening this file sees the full shape of a
Trip without reading the parsing code.
"""
from dataclasses import dataclass, field


@dataclass
class DispatchRound:
    """One round of: candidates considered -> one assigned -> received/rejected."""
    round_number: int
    candidates: list  # list of dicts: driver_id, distance, eta, selection_type
    assigned_driver_id: int | None
    assigned_at: int | None  # created_at of driver_assigned
    outcome: str  # "accepted" / "rejected" / "all_rejected" / "unknown"


@dataclass
class DispatchHistory:
    rounds: list = field(default_factory=list)
    real_driver_id: int | None = None       # resolved per SRS-1
    total_rejections: int = 0
    cancelled_after_accept: bool = False    # dispute flag, see SRS-3
    bidding: bool = False
    blast_dispatch: bool = False


@dataclass
class StopRow:
    stop_number: int
    planned_address: str
    planned_lat: float | None
    planned_lng: float | None
    actual_address: str
    actual_lat: float | None
    actual_lng: float | None
    arrival_status: str
    arrival_time: str


@dataclass
class StopBreakdown:
    pickup: dict
    drops_planned: list
    stops: list  # list[StopRow]
    mid_trip_update_detected: bool = False  # True if a trip_updated event was found


@dataclass
class FareBreakdown:
    currency: str
    distance_km: float | None
    duration_sec: int | None
    base_fare: float | None
    distance_fare: str
    duration_fare: str
    waiting_fare: str
    is_upfront: bool
    price_file_rows: dict  # {"additional_charge": [...], "distance_fare": [...], "waiting_fare": [...]}


@dataclass
class ActualOutcome:
    driver_id: int | None
    actual_pickup_address: str | None
    actual_drop_address: str | None
    trip_start_time: str | None
    driver_arrived_time: str | None
    trip_end_notification_time: str | None
    passenger_wait_time_sec: int | None
    driver_wait_time_sec: int | None
    end_notif_to_ended_gap_sec: int | None
    distance_travelled_m: int | None
    waiting_time_sec: int | None
    trip_cost: float | None
    promo_code: str | None
    discount: float | None
    tip: float | None
    payment_method_label: str | None
    actual_duration_sec: int | None
    requested_vehicle_label: str | None
    assigned_vehicle_label: str | None
    vehicle_mismatch: bool = False   # True if requested != assigned model


@dataclass
class Trip:
    trip_id: int
    service_group: str
    module_label: str
    booked_by_label: str
    passenger_id: int | None
    vehicle_type_label: str
    is_corporate: bool
    is_pooled: bool
    pooled_with: str
    is_bidding: bool
    is_pre_booked: bool
    promo_code_at_creation: str
    stops: StopBreakdown
    fare: FareBreakdown | None
    dispatch: DispatchHistory
    outcome: ActualOutcome | None
    raw_events: list = field(default_factory=list)
    source_filename: str = ""
