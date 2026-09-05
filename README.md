# ASG Airlines data engineering case study

This project cleans the supplied ASG Airlines flight, booking, payment, and passenger records and produces a reporting-ready analytical dataset.

## Deliverables

| Deliverable | Location |
| --- | --- |
| Pipeline | `src/pipeline.py` |
| Data-model DDL | `src/warehouse_schema.sql` |
| Validation tests | `src/test_pipeline.py` |
| Cleaned data and KPI tables | `data/processed/` |
| Excel operations dashboard | `outputs/ASG_Airlines_Operations.xlsx` |
| Dashboard screenshot | `powerbi/operations_dashboard_preview.png` |
| Power BI report | `powerbi/ASG_Airlines_Operations.pbix` |
| Power BI build guide and measures | `powerbi/README.md` and `powerbi/measures.dax` |
| Solution walkthrough | `docs/ASG_Airlines_Case_Study.docx` |

## Run the pipeline

Use Python 3.11 or later and install `pandas` plus an Excel engine such as `openpyxl`.

```powershell
$env:ASG_PII_SALT = "use-a-secret-value-outside-source-control"
python src/pipeline.py --input "data/raw/UseCase - Airlines.xlsx" --output data/processed
python -m unittest src/test_pipeline.py
```

The pipeline validates required sheets, standardizes text and timestamps, removes exact duplicate flight rows, rejects invalid flight records, corrects overnight arrivals, creates duration and anomaly fields, masks passenger identifiers with a salted SHA-256 key, and writes dimensions, facts, KPI tables, a quality summary, rejected records, and a run log.

## Data model

`dim_flight` is the operational flight-schedule dimension. `fact_booking` links to passengers through `passenger_key`, and `fact_payment` links to bookings through `booking_id`.

The supplied booking data has no schedule timestamp. When a flight ID occurs on multiple schedules, the pipeline marks the booking as `Ambiguous flight ID` rather than assigning it to an arbitrary schedule.

## Power BI report

The completed report is `powerbi/ASG_Airlines_Operations.pbix`. It contains five pages:

1. Operations Summary
2. Duration Analysis
3. Route Performance
4. Airline Trends
5. Delay and Anomaly Insights

The report includes KPI cards, airline and route analysis, booking-status distribution, duration analysis, anomaly details, and interactive slicers.

The source data does not contain scheduled and actual flight timestamps. Therefore, the Delay and Anomaly Insights page reports duration and data-quality anomalies, not flight punctuality or on-time performance.

To refresh the report after the curated CSV files change:

1. Open the PBIX in Power BI Desktop.
2. Update file-source paths if necessary.
3. Select **Refresh**.
4. Review slicers, measures, relationships, and visuals.
5. Save the PBIX.

The detailed source mappings, relationships, and DAX measures are available in `powerbi/PowerBIReadme.md` and `powerbi/measures.dax`.

## Privacy

Do not publish the original source workbook or `data/raw/` to a public repository. They contain direct passenger identifiers.

Curated outputs exclude first and last names, email addresses, phone numbers, Aadhaar IDs, passport numbers, emergency-contact names, and emergency-contact phone numbers. Passenger records use a salted SHA-256 `passenger_key` instead of the original passenger ID.