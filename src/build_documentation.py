"""Create the ASG Airlines case-study walkthrough document."""

from pathlib import Path
import json

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "ASG_Airlines_Case_Study.docx"
ASSETS = ROOT / "docs" / "assets"
QUALITY = json.loads((ROOT / "data" / "processed" / "data_quality_summary.json").read_text(encoding="utf-8"))


def shade(cell, color):
    tc_pr = cell._tc.get_or_add_tcPr()
    fill = OxmlElement("w:shd")
    fill.set(qn("w:fill"), color)
    tc_pr.append(fill)


def set_cell_border(cell, color="D9D9D9"):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "6")
        element.set(qn("w:color"), color)


def format_table(table, header_color="17365D"):
    for row_index, row in enumerate(table.rows):
        for cell in row.cells:
            set_cell_border(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.margin_top = cell.margin_bottom = 90
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(2)
                for run in p.runs:
                    run.font.name = "Arial"
                    run.font.size = Pt(9)
            if row_index == 0:
                shade(cell, header_color)
                for run in cell.paragraphs[0].runs:
                    run.font.color.rgb = RGBColor(255, 255, 255)
                    run.font.bold = True
            elif row_index % 2 == 0:
                shade(cell, "F3F7FB")


def add_table(doc, headings, rows, widths=None):
    table = doc.add_table(rows=1, cols=len(headings))
    table.style = "Table Grid"
    for i, heading in enumerate(headings):
        table.cell(0, i).text = str(heading)
    for values in rows:
        cells = table.add_row().cells
        for i, value in enumerate(values):
            cells[i].text = str(value)
    if widths:
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Inches(width)
    format_table(table)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return table


def heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.name = "Arial"
        run.font.color.rgb = RGBColor(0, 0, 0)
    return p


def body(doc, text, bold_lead=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.08
    if bold_lead:
        r = p.add_run(bold_lead)
        r.bold = True
        p.add_run(text)
    else:
        p.add_run(text)
    for run in p.runs:
        run.font.name = "Arial"
        run.font.size = Pt(10)
    return p


def bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(text)
    for run in p.runs:
        run.font.name = "Arial"
        run.font.size = Pt(10)
    return p


def diagram(path, title, nodes, arrows):
    """Create a simple, high-resolution diagram that renders reliably in Word."""
    image = Image.new("RGB", (1600, 520), "white")
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("arialbd.ttf", 32)
        node_font = ImageFont.truetype("arial.ttf", 23)
    except OSError:
        title_font = node_font = ImageFont.load_default()
    draw.text((45, 25), title, fill="#000000", font=title_font)
    for x, y, width, height, label, color in nodes:
        draw.rounded_rectangle((x, y, x + width, y + height), radius=20, fill=color, outline="#17365D", width=3)
        box = draw.multiline_textbbox((0, 0), label, font=node_font, spacing=5, align="center")
        tx = x + (width - (box[2] - box[0])) / 2
        ty = y + (height - (box[3] - box[1])) / 2
        draw.multiline_text((tx, ty), label, fill="#000000", font=node_font, spacing=5, align="center")
    for x1, y1, x2, y2 in arrows:
        draw.line((x1, y1, x2, y2), fill="#17365D", width=5)
        draw.polygon(((x2, y2), (x2 - 16, y2 - 9), (x2 - 16, y2 + 9)), fill="#17365D")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def create_diagrams():
    diagram(
        ASSETS / "solution_architecture.png",
        "Solution architecture",
        [
            (60, 190, 250, 110, "Source workbook\nFlights Bookings Payments Passengers", "#D9EAF7"),
            (430, 190, 250, 110, "Raw zone\nImmutable source copy", "#EAF2F8"),
            (800, 190, 250, 110, "Python pipeline\nValidate Clean Mask Aggregate", "#D9EAD3"),
            (1170, 190, 300, 110, "Curated CSV tables\nPower BI reporting model", "#FFF2CC"),
        ],
        [(310, 245, 410, 245), (680, 245, 780, 245), (1050, 245, 1150, 245)],
    )
    diagram(
        ASSETS / "data_flow.png",
        "Data flow and quality controls",
        [
            (50, 170, 210, 130, "Ingest\nRequired-sheet check", "#D9EAF7"),
            (330, 170, 210, 130, "Standardize\nText Times Amounts", "#EAF2F8"),
            (610, 170, 210, 130, "Validate\nIDs Routes Required fields", "#FCE4D6"),
            (890, 170, 210, 130, "Transform\nDeduplicate Overnight PII", "#D9EAD3"),
            (1170, 170, 330, 130, "Publish\nFacts Dimensions KPIs Logs", "#FFF2CC"),
        ],
        [(260, 235, 310, 235), (540, 235, 590, 235), (820, 235, 870, 235), (1100, 235, 1150, 235)],
    )
    diagram(
        ASSETS / "data_model.png",
        "Curated analytical data model",
        [
            (85, 120, 280, 120, "dim flight\nflight schedule key\nroute duration anomaly", "#D9EAF7"),
            (85, 330, 280, 120, "dim passenger masked\npassenger key age band", "#D9EAF7"),
            (650, 220, 300, 120, "fact booking\nbooking key passenger key\nflight schedule key", "#D9EAD3"),
            (1190, 220, 300, 120, "fact payment\npayment key booking key\namount method", "#FFF2CC"),
        ],
        [(365, 180, 630, 255), (365, 390, 630, 305), (950, 280, 1170, 280)],
    )


def main():
    create_diagrams()
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)
    styles = doc.styles
    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(10)
    styles["Title"].font.name = "Arial"
    styles["Title"].font.size = Pt(22)
    styles["Title"].font.color.rgb = RGBColor(0, 0, 0)

    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title.add_run("ASG Airlines Data Engineering Case Study")
    body(doc, "This document describes the local end-to-end pipeline, curated data model, data-quality controls, privacy measures, and reporting design created from the supplied airline workbook. The resulting analytical tables are ready to load into Power BI or another BI tool.")
    body(doc, "Outcome: the pipeline converts 1,020 raw flight rows into 1,005 unique curated flight schedules, corrects one overnight arrival date, and isolates operational anomalies for reporting.")

    heading(doc, "Solution Architecture")
    body(doc, "The implementation uses a repeatable local Python pipeline. It follows a medallion-style flow that can be mapped directly to cloud storage and orchestration services when the workload grows.")
    doc.add_picture(str(ASSETS / "solution_architecture.png"), width=Inches(6.85))
    add_table(doc, ["Layer", "Component", "Purpose"], [
        ["Source", "UseCase - Airlines.xlsx", "Supplied flights, bookings, payments, and passengers sheets."],
        ["Raw", "data/raw", "Immutable copied source workbook for reproducible ingestion."],
        ["Transform", "src/pipeline.py", "Schema validation, deduplication, standardization, overnight handling, PII protection, and KPI generation."],
        ["Curated", "data/processed", "CSV dimensions, facts, KPI tables, rejected-record output, quality summary, and log."],
        ["Consumption", "Operations workbook and Power BI", "Business KPIs, route performance, airline distribution, and anomaly monitoring."],
    ], [1.0, 1.8, 4.7])
    heading(doc, "Data Flow")
    doc.add_picture(str(ASSETS / "data_flow.png"), width=Inches(6.85))
    add_table(doc, ["Step", "Flow"], [
        ["1", "Read each required worksheet and fail fast if a required sheet is absent."],
        ["2", "Normalize identifiers, text values, timestamps, and numeric payment values."],
        ["3", "Remove exact duplicate flight rows and direct invalid records to rejected_flights.csv."],
        ["4", "Derive airline names from valid flight prefixes and calculate corrected flight durations."],
        ["5", "Mask passenger identifiers and remove passport and emergency-contact fields before producing curated outputs."],
        ["6", "Create dimensions, facts, business KPI aggregates, a data-quality summary, and the reporting workbook."],
    ], [0.7, 6.8])

    heading(doc, "Source Dataset")
    add_table(doc, ["Sheet", "Grain", "Use in solution"], [
        ["flights", "Flight schedule record", "Operational duration, route, airline, and anomaly analysis."],
        ["bookings", "Booking", "Booking status, seat, and masked passenger relationship."],
        ["payments", "Payment", "Payment amount and payment method analysis."],
        ["passengers", "Passenger", "Masked passenger dimension with age band and gender retained for permitted analysis."],
    ], [1.4, 1.7, 4.4])

    heading(doc, "Data Cleaning and Transformation Logic")
    add_table(doc, ["Rule", "Implementation"], [
        ["Flight identifiers", "Trim whitespace, uppercase values, validate AI, 6F, SJ, or UK followed by three digits. Invalid records are rejected rather than silently changed."],
        ["Airline standardization", "Replace blank and UNKNOWN values using flight prefix mappings: AI Air India, 6F IndiGo, SJ SpiceJet, UK Vistara."],
        ["Duplicates", f"Drop only exact duplicate flight rows. {QUALITY['exact_duplicate_flights_removed']} rows were removed. Repeated flight numbers with different schedule details remain valid records."],
        ["Time parsing", "Convert departure and arrival to timestamps. Records missing a required timestamp are rejected."],
        ["Overnight flights", "If arrival precedes departure, add exactly one day to arrival, then recompute duration. This corrected one supplied flight."],
        ["Duration", "Calculate duration_minutes from corrected arrival minus departure. Source duration text is not used as the reporting metric."],
        ["Anomalies", "Flag flights under 45 minutes, over 360 minutes, or adjusted for a cross-day arrival. Anomalies are preserved for investigation."],
        ["Payments", "Convert amount to numeric. Blank values remain null and are counted as a data-quality issue rather than treated as zero."],
    ], [1.55, 5.95])

    heading(doc, "Data Model")
    body(doc, "The reporting model uses a star-like structure. dim_flight supports route and duration analysis. fact_booking links operational flight identifiers to booking outcomes. fact_payment links to bookings for revenue analysis. dim_passenger_masked contains no direct passenger identifiers.")
    doc.add_picture(str(ASSETS / "data_model.png"), width=Inches(6.85))
    add_table(doc, ["Table", "Primary key", "Relationships and purpose"], [
        ["dim_flight", "flight_schedule_key", "One record per distinct flight schedule. Includes route, timestamps, corrected duration, and anomaly fields."],
        ["fact_booking", "booking_id", "Many bookings to a flight number; contains masked passenger key, booking status, and seat number."],
        ["fact_payment", "payment_id", "Many payments to bookings; contains amount, method, and payment status."],
        ["dim_passenger_masked", "passenger_key", "One masked passenger record with age band, gender, and date of birth."],
    ], [1.6, 1.6, 4.3])
    body(doc, "Modeling note: the booking source has flight_id but no scheduled departure timestamp. When a flight number maps to more than one schedule, the pipeline leaves flight_schedule_key blank and labels the booking as Ambiguous flight ID. A production source should carry a unique flight-instance or schedule identifier in bookings.")

    heading(doc, "Data Quality Results")
    add_table(doc, ["Measure", "Result"], [
        ["Raw flight rows", QUALITY["raw_flight_rows"]],
        ["Curated flight schedules", QUALITY["accepted_flight_rows"]],
        ["Exact duplicate rows removed", QUALITY["exact_duplicate_flights_removed"]],
        ["Rejected flight rows", QUALITY["rejected_flight_rows"]],
        ["Overnight arrivals corrected", QUALITY["overnight_arrivals_corrected"]],
        ["Flagged flight anomalies", QUALITY["flight_anomalies"]],
        ["Missing payment amounts", QUALITY["missing_payment_amounts"]],
        ["Ambiguous flight-ID bookings", QUALITY["ambiguous_flight_id_bookings"]],
    ], [4.6, 2.9])

    heading(doc, "Business KPIs")
    add_table(doc, ["KPI", "Definition"], [
        ["Average flight duration", "Mean duration_minutes from dim_flight after overnight correction."],
        ["Route-wise traffic", "Count of curated flight schedules by source and destination route."],
        ["Flight anomalies", "Count and detail of records with short duration, long duration, or corrected arrival date."],
        ["Flights by airline", "Count of curated flight schedules by standardized airline."],
        ["Confirmed bookings", "Count of booking records whose status equals CONFIRMED."],
        ["Recorded payment amount", "Sum of non-null payment amounts. Null amounts remain excluded and visible as a quality issue."],
    ], [2.0, 5.5])

    heading(doc, "Privacy and Access Control")
    body(doc, "The raw source includes passenger names, email addresses, phone numbers, Aadhaar IDs, passport numbers, and emergency contact details. These direct identifiers are not included in the curated reporting model.")
    for item in [
        "Replace passenger_id with a salted SHA-256 passenger_key before writing curated booking and passenger tables.",
        "Exclude first name, last name, email, phone, Aadhaar ID, passport number, emergency contact name, and emergency contact phone from curated outputs.",
        "Use a managed secret for ASG_PII_SALT in production and never store the secret with the data or source code.",
        "Restrict raw-zone access to ingestion and authorized data-steward roles. Grant BI users read access only to curated tables.",
        "Enable storage encryption, access logging, retention rules, and periodic access reviews in a cloud deployment.",
    ]:
        bullet(doc, item)

    heading(doc, "Power BI Reporting Design")
    body(doc, "Load dim_flight.csv, fact_booking.csv, fact_payment.csv, dim_passenger_masked.csv, and the KPI files from data/processed. Relate fact_payment to fact_booking on booking_id. Relate fact_booking to dim_flight on flight_schedule_key only after a flight-instance key is available for all booking records.")
    add_table(doc, ["Page", "Visuals and controls"], [
        ["Operations Summary", "KPI cards for flights, average duration, overnight flights, anomalies, bookings, and payment amount; donut chart for airline share."],
        ["Duration Analysis", "Duration-band column chart, average duration card, and airline and route slicers."],
        ["Route Performance", "Sorted route traffic bar chart, average duration by route, and airline slicer."],
        ["Airline Trends", "Flights by airline, duration comparison, booking status breakdown, and date slicer."],
        ["Delay and Anomaly Insights", "Anomaly count card, anomaly-type breakdown, detailed table, and route/airline filters."],
    ], [1.8, 5.7])

    heading(doc, "Assumptions and Production Extension")
    for item in [
        "Airport codes are expected to be three-character IATA-like codes and source must differ from destination.",
        "An earlier arrival timestamp is treated as an overnight flight only once; a resulting duration outside the anomaly thresholds remains visible for review.",
        "The source does not contain scheduled versus actual timestamps, so delay minutes cannot be calculated. The delivered anomaly metrics are data-quality and duration exceptions, not carrier punctuality measurements.",
        "For Azure deployment, orchestrate ingestion with Azure Data Factory, store raw and curated data in ADLS Gen2, transform with Databricks or Synapse, govern access through Microsoft Entra ID and Key Vault, and connect Power BI to curated Delta or SQL tables.",
    ]:
        bullet(doc, item)

    doc.core_properties.title = "ASG Airlines Data Engineering Case Study"
    doc.core_properties.author = "ASG Airlines"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)


if __name__ == "__main__":
    main()
