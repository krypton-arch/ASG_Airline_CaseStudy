# Power BI report guide

## Report file

The completed Power BI report is:

```text
ASG_Airlines_Operations.pbix
```

The report contains five pages:

1. Operations Summary
2. Duration Analysis
3. Route Performance
4. Airline Trends
5. Delay and Anomaly Insights

## Data sources

The report uses the following curated files from `data/processed/`:

- `dim_flight.csv`
- `fact_booking.csv`
- `fact_payment.csv`
- `dim_passenger_masked.csv`

Set the following column data types after import:

| Table | Column | Data type |
| --- | --- | --- |
| dim_flight | departure_time | Date/Time |
| dim_flight | arrival_time | Date/Time |
| dim_flight | departure_date | Date |
| dim_flight | duration_minutes | Whole Number |
| dim_flight | overnight_adjusted | True/False |
| dim_flight | has_anomaly | True/False |
| fact_booking | booking_date | Date/Time |
| fact_payment | amount | Fixed decimal number |

## Relationships

Create these active, single-direction, one-to-many relationships:

| One side | Many side |
| --- | --- |
| `dim_passenger_masked[passenger_key]` | `fact_booking[passenger_key]` |
| `dim_flight[flight_schedule_key]` | `fact_booking[flight_schedule_key]` |
| `fact_booking[booking_id]` | `fact_payment[booking_id]` |

Do not create a relationship using `airline`. Airline values repeat across many flight records and are used directly in slicers and visuals.

Some booking records have `flight_match_status` equal to `Ambiguous flight ID`. These rows remain unmatched to a flight schedule because the source booking data does not include a unique flight-instance timestamp.

## DAX measures

The report uses the measures in `measures.dax`:

- Total Flights
- Average Flight Duration Minutes
- Overnight Flights
- Flight Anomalies
- Total Bookings
- Confirmed Bookings
- Recorded Payment Amount
- Missing Payment Amounts

## Page design

### Operations Summary

- KPI cards for Total Flights, Average Flight Duration Minutes, Flight Anomalies, and Recorded Payment Amount.
- Donut chart showing Flights by airline.
- Airline and departure-date slicers.

### Duration Analysis

- Clustered column chart showing Flights by duration band.
- Average Flight Duration card.
- Route and airline slicers.

### Route Performance

- Descending bar chart showing Flights by route.
- Table containing route, Total Flights, Average Flight Duration Minutes, and Flight Anomalies.
- Airline slicer.

### Airline Trends

- Bar chart showing Flights by airline.
- Bar chart showing Average Flight Duration by airline.
- Donut chart showing Bookings by status.
- Departure-date slicer.

### Delay and Anomaly Insights

- Flight Anomalies KPI card.
- Bar chart showing Anomalies by type.
- Filtered table containing flight ID, airline, route, departure timestamp, arrival timestamp, duration minutes, and anomaly type.
- Airline and route slicers.

This page reports duration and data-quality anomalies. It must not be described as punctuality or on-time performance analysis because the source data does not include scheduled-versus-actual flight timestamps.

## Refresh instructions

1. Open `ASG_Airlines_Operations.pbix` in Power BI Desktop.
2. Select **Refresh**.
3. Update file-source paths if Power BI cannot locate the curated CSV files.
4. Confirm that all visuals, measures, relationships, and slicers load correctly.
5. Save the PBIX file.

## Privacy

The Power BI report must use only curated datasets.

Do not import or publish `data/raw/` or the original source workbook. They contain direct passenger identifiers. Curated outputs use `passenger_key` and exclude names, email addresses, phone numbers, Aadhaar IDs, passport numbers, and emergency-contact details.