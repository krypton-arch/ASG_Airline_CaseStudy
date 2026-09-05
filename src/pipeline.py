"""Build curated ASG Airlines analytical tables from the supplied workbook."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
from pathlib import Path

import pandas as pd


FLIGHT_PATTERN = re.compile(r"^(AI|6F|SJ|UK)\d{3}$")
AIRLINE_BY_PREFIX = {"AI": "Air India", "6F": "IndiGo", "SJ": "SpiceJet", "UK": "Vistara"}
PII_SALT = os.environ.get("ASG_PII_SALT", "asg-local-development-salt")


def setup_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )
    return logging.getLogger("asg_pipeline")


def stable_hash(value: object) -> str:
    return hashlib.sha256(f"{PII_SALT}|{value}".encode("utf-8")).hexdigest()


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")


def load_source(input_path: Path) -> dict[str, pd.DataFrame]:
    required = {"flights", "bookings", "payments", "passengers"}
    workbook = pd.ExcelFile(input_path)
    missing = required.difference(workbook.sheet_names)
    if missing:
        raise ValueError(f"Missing required sheets: {', '.join(sorted(missing))}")
    return {sheet: pd.read_excel(input_path, sheet_name=sheet) for sheet in required}


def build_flights(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    flights = raw.copy()
    for column in ["flight_id", "airline", "source", "destination"]:
        flights[column] = flights[column].astype("string").str.strip().str.upper()
    flights["flight_id"] = flights["flight_id"].str.replace(r"\s+", "", regex=True)
    flights["departure_time"] = pd.to_datetime(flights["departure_time"], errors="coerce")
    flights["arrival_time"] = pd.to_datetime(flights["arrival_time"], errors="coerce")

    exact_duplicates = int(flights.duplicated().sum())
    flights = flights.drop_duplicates().copy()
    flights["airline"] = flights["airline"].replace({"<NA>": pd.NA, "NAN": pd.NA, "UNKNOWN": pd.NA})
    flights["airline_derived"] = flights["flight_id"].str[:2].map(AIRLINE_BY_PREFIX)
    flights["airline"] = flights["airline"].fillna(flights["airline_derived"])
    flights["airline"] = flights["airline"].str.title().replace({"Indigo": "IndiGo"})

    valid_id = flights["flight_id"].str.match(FLIGHT_PATTERN, na=False)
    required_values = flights[["flight_id", "airline", "source", "destination", "departure_time", "arrival_time"]].notna().all(axis=1)
    valid_route = flights["source"].ne(flights["destination"])
    accepted = valid_id & required_values & valid_route
    rejected = flights.loc[~accepted].copy()
    rejected["rejection_reason"] = "Invalid flight identifier, missing required value, or identical route endpoints"
    flights = flights.loc[accepted].copy()

    # A timestamp earlier than departure is a cross-day arrival. Only roll it one day;
    # anything still outside the permitted window becomes an anomaly instead of being hidden.
    flights["overnight_adjusted"] = flights["arrival_time"] < flights["departure_time"]
    flights.loc[flights["overnight_adjusted"], "arrival_time"] += pd.Timedelta(days=1)
    flights["duration_minutes"] = ((flights["arrival_time"] - flights["departure_time"]).dt.total_seconds() / 60).round().astype("Int64")
    flights["route"] = flights["source"] + " - " + flights["destination"]
    flights["departure_date"] = flights["departure_time"].dt.date
    flights["departure_hour"] = flights["departure_time"].dt.hour
    flights["duration_band"] = pd.cut(
        flights["duration_minutes"],
        bins=[0, 90, 180, 300, float("inf")],
        labels=["Up to 90 min", "91 to 180 min", "181 to 300 min", "Over 300 min"],
        include_lowest=True,
    ).astype("string")
    flights["anomaly_type"] = pd.NA
    flights.loc[flights["duration_minutes"].lt(45), "anomaly_type"] = "Short duration under 45 minutes"
    flights.loc[flights["duration_minutes"].gt(360), "anomaly_type"] = "Long duration over 360 minutes"
    flights.loc[flights["overnight_adjusted"], "anomaly_type"] = "Arrival date corrected for overnight flight"
    flights["has_anomaly"] = flights["anomaly_type"].notna()
    flights["flight_schedule_key"] = pd.Series(
        [
            stable_hash(f"{r.flight_id}|{r.departure_time.isoformat()}|{r.source}|{r.destination}")[:20]
            for r in flights.itertuples(index=False)
        ],
        index=flights.index,
        dtype="string",
    )
    flights = flights.drop(columns=["duration", "airline_derived"])
    metrics = {
        "raw_flight_rows": len(raw),
        "exact_duplicate_flights_removed": exact_duplicates,
        "rejected_flight_rows": len(rejected),
        "accepted_flight_rows": len(flights),
        "overnight_arrivals_corrected": int(flights["overnight_adjusted"].sum()),
        "flight_anomalies": int(flights["has_anomaly"].sum()),
    }
    return flights, rejected, metrics


def build_bookings(raw: pd.DataFrame, valid_flights: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    bookings = raw.copy()
    for column in ["booking_id", "passenger_id", "flight_id", "status"]:
        bookings[column] = bookings[column].astype("string").str.strip().str.upper()
    bookings["booking_date"] = pd.to_datetime(bookings["booking_date"], errors="coerce")
    bookings["status"] = bookings["status"].fillna("UNKNOWN")
    bookings["passenger_key"] = bookings["passenger_id"].map(stable_hash)
    bookings = bookings.drop(columns=["passport_number", "emergency_contact_name", "emergency_contact_phone", "passenger_id"])
    # Bookings do not contain a scheduled departure timestamp. Link only when an
    # identifier uniquely identifies one schedule; otherwise retain the booking
    # at flight-number grain and explicitly flag the unresolved relationship.
    schedule_counts = valid_flights.groupby("flight_id")["flight_schedule_key"].size()
    schedules = valid_flights.loc[valid_flights["flight_id"].map(schedule_counts).eq(1)]
    bookings = bookings.merge(
        schedules[["flight_id", "flight_schedule_key", "airline", "route", "duration_minutes", "has_anomaly"]],
        on="flight_id", how="left", validate="m:1"
    )
    bookings["flight_match_status"] = bookings["flight_schedule_key"].notna().map({True: "Matched", False: "Unmatched"})
    ambiguous_ids = set(schedule_counts[schedule_counts.gt(1)].index)
    bookings.loc[bookings["flight_id"].isin(ambiguous_ids), "flight_match_status"] = "Ambiguous flight ID"
    metrics = {
        "raw_booking_rows": len(raw),
        "unmatched_bookings": int(bookings["flight_match_status"].eq("Unmatched").sum()),
        "ambiguous_flight_id_bookings": int(bookings["flight_match_status"].eq("Ambiguous flight ID").sum()),
    }
    return bookings, metrics


def build_passengers(raw: pd.DataFrame) -> pd.DataFrame:
    passengers = raw.copy()
    passengers["passenger_id"] = passengers["passenger_id"].astype("string").str.strip().str.upper()
    passengers["age"] = pd.to_numeric(passengers["age"], errors="coerce")
    passengers["date_of_birth"] = pd.to_datetime(passengers["date_of_birth"], errors="coerce")
    passengers["passenger_key"] = passengers["passenger_id"].map(stable_hash)
    passengers["age_band"] = pd.cut(
        passengers["age"], bins=[0, 17, 34, 54, 120], labels=["Under 18", "18 to 34", "35 to 54", "55 and over"], include_lowest=True
    ).astype("string")
    return passengers[["passenger_key", "age_band", "gender", "date_of_birth"]].drop_duplicates("passenger_key")


def build_payments(raw: pd.DataFrame) -> pd.DataFrame:
    payments = raw.copy()
    payments["booking_id"] = payments["booking_id"].astype("string").str.strip().str.upper()
    payments["amount"] = pd.to_numeric(payments["amount"], errors="coerce")
    payments["payment_method"] = payments["payment_method"].astype("string").str.strip().str.upper()
    payments["payment_status"] = payments["amount"].notna().map({True: "Recorded", False: "Missing amount"})
    return payments


def build_kpis(flights: pd.DataFrame, bookings: pd.DataFrame, payments: pd.DataFrame) -> dict[str, pd.DataFrame]:
    booking_payments = bookings.merge(payments[["booking_id", "amount", "payment_method", "payment_status"]], on="booking_id", how="left")
    overview = pd.DataFrame([
        ["Flights", len(flights)],
        ["Average flight duration minutes", round(flights["duration_minutes"].mean(), 1)],
        ["Overnight flights", int(flights["overnight_adjusted"].sum())],
        ["Flight anomalies", int(flights["has_anomaly"].sum())],
        ["Bookings", len(bookings)],
        ["Confirmed bookings", int(bookings["status"].eq("CONFIRMED").sum())],
        ["Recorded payment amount", round(payments["amount"].sum(), 2)],
        ["Missing payment amounts", int(payments["amount"].isna().sum())],
    ], columns=["metric", "value"])
    route = flights.groupby("route", as_index=False).agg(
        flights=("flight_schedule_key", "count"), average_duration_minutes=("duration_minutes", "mean"), anomalies=("has_anomaly", "sum")
    ).sort_values("flights", ascending=False)
    route["average_duration_minutes"] = route["average_duration_minutes"].round(1)
    airline = flights.groupby("airline", as_index=False).agg(
        flights=("flight_schedule_key", "count"), average_duration_minutes=("duration_minutes", "mean"), anomalies=("has_anomaly", "sum")
    ).sort_values("flights", ascending=False)
    airline["average_duration_minutes"] = airline["average_duration_minutes"].round(1)
    anomalies = flights.loc[flights["has_anomaly"], ["flight_id", "airline", "route", "departure_time", "arrival_time", "duration_minutes", "anomaly_type"]]
    return {"fact_booking_enriched": booking_payments, "kpi_overview": overview, "kpi_route_traffic": route, "kpi_airline_distribution": airline, "kpi_anomalies": anomalies}


def run(input_path: Path, output_dir: Path) -> None:
    logger = setup_logging(output_dir / "pipeline.log")
    output_dir.mkdir(parents=True, exist_ok=True)
    source = load_source(input_path)
    logger.info("Loaded source workbook: %s", input_path.name)
    flights, rejected, quality = build_flights(source["flights"])
    bookings, booking_quality = build_bookings(source["bookings"], flights)
    passengers = build_passengers(source["passengers"])
    payments = build_payments(source["payments"])
    quality.update(booking_quality)
    quality.update({"raw_payment_rows": len(source["payments"]), "missing_payment_amounts": int(payments["amount"].isna().sum()), "raw_passenger_rows": len(source["passengers"])})
    outputs = {"dim_flight": flights, "dim_passenger_masked": passengers, "fact_booking": bookings, "fact_payment": payments, "rejected_flights": rejected}
    outputs.update(build_kpis(flights, bookings, payments))
    for name, frame in outputs.items():
        write_csv(frame, output_dir / f"{name}.csv")
    (output_dir / "data_quality_summary.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    logger.info("Created %s curated tables. Accepted flights: %s", len(outputs), quality["accepted_flight_rows"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASG Airlines local data engineering pipeline")
    parser.add_argument("--input", default="data/raw/UseCase - Airlines.xlsx")
    parser.add_argument("--output", default="data/processed")
    args = parser.parse_args()
    run(Path(args.input), Path(args.output))
