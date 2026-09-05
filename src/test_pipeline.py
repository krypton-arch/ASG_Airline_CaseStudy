"""Regression checks for the ASG Airlines transformation rules."""

import unittest

import pandas as pd

from pipeline import build_flights, build_passengers


class FlightTransformationTests(unittest.TestCase):
    def test_overnight_arrival_is_corrected(self):
        raw = pd.DataFrame([{
            "flight_id": " AI101 ", "airline": "unknown", "source": "del", "destination": "bom",
            "departure_time": "2026-01-01 23:30:00", "arrival_time": "2026-01-01 01:00:00", "duration": None,
        }])
        flights, rejected, metrics = build_flights(raw)
        self.assertTrue(rejected.empty)
        self.assertEqual(metrics["overnight_arrivals_corrected"], 1)
        self.assertEqual(int(flights.iloc[0]["duration_minutes"]), 90)
        self.assertEqual(flights.iloc[0]["airline"], "Air India")

    def test_invalid_identifier_is_rejected(self):
        raw = pd.DataFrame([{
            "flight_id": "BAD", "airline": "Unknown", "source": "DEL", "destination": "BOM",
            "departure_time": "2026-01-01 10:00:00", "arrival_time": "2026-01-01 12:00:00", "duration": None,
        }])
        flights, rejected, _ = build_flights(raw)
        self.assertTrue(flights.empty)
        self.assertEqual(len(rejected), 1)

    def test_passenger_pii_is_excluded(self):
        raw = pd.DataFrame([{
            "passenger_id": "P1000", "first_name": "A", "last_name": "B", "age": 28, "gender": "F",
            "email": "a@example.com", "phone": "123", "aadhaar_id": "123", "date_of_birth": "1998-01-01",
        }])
        masked = build_passengers(raw)
        self.assertEqual(set(masked.columns), {"passenger_key", "age_band", "gender", "date_of_birth"})
        self.assertNotEqual(masked.iloc[0]["passenger_key"], "P1000")


if __name__ == "__main__":
    unittest.main()
