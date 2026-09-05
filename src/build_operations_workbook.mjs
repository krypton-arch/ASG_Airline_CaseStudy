import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const processedDir = new URL("../data/processed/", import.meta.url);
const outputPath = new URL("../outputs/ASG_Airlines_Operations.xlsx", import.meta.url);
const previewPath = new URL("../powerbi/operations_dashboard_preview.png", import.meta.url);

function parseCsv(text) {
  const rows = [];
  let row = [], value = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      if (quoted && text[i + 1] === '"') { value += '"'; i++; } else quoted = !quoted;
    } else if (c === ',' && !quoted) { row.push(value); value = ""; }
    else if ((c === '\n' || c === '\r') && !quoted) {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(value); if (row.some(v => v !== "")) rows.push(row); row = []; value = "";
    } else value += c;
  }
  if (value || row.length) { row.push(value); rows.push(row); }
  return rows;
}

async function csv(name) { return parseCsv(await fs.readFile(new URL(name, processedDir), "utf8")); }
function num(v) { const n = Number(v); return Number.isFinite(n) ? n : 0; }
function header(sheet, range) {
  sheet.getRange(range).format = { fill: "#17365D", font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
}
function section(sheet, range) {
  sheet.getRange(range).format = { fill: "#D9EAF7", font: { name: "Arial", size: 11, bold: true, color: "#000000" } };
}

const [overview, routes, airlines, anomalies, flights] = await Promise.all([
  csv("kpi_overview.csv"), csv("kpi_route_traffic.csv"), csv("kpi_airline_distribution.csv"), csv("kpi_anomalies.csv"), csv("dim_flight.csv"),
]);
const wb = Workbook.create();
const dash = wb.worksheets.add("Operations Summary");
const routeSheet = wb.worksheets.add("Route Performance");
const airlineSheet = wb.worksheets.add("Airline Trends");
const anomalySheet = wb.worksheets.add("Duration Anomalies");
const dataSheet = wb.worksheets.add("Flight Data");

for (const sheet of [dash, routeSheet, airlineSheet, anomalySheet, dataSheet]) {
  sheet.showGridLines = false;
  sheet.getRange("A:Z").format.font = { name: "Arial", size: 10, color: "#222222" };
}

dash.mergeCells("A1:H1");
dash.getRange("A1").values = [["ASG Airlines Flight Operations"]];
dash.getRange("A1").format = { font: { name: "Arial", size: 18, bold: true, color: "#17365D" }, verticalAlignment: "center" };
dash.getRange("A2:H2").merge();
dash.getRange("A2").values = [["Operational KPIs based on the curated flight, booking, and payment data"]];
dash.getRange("A2").format = { font: { name: "Arial", size: 10, italic: true, color: "#666666" } };
const metrics = Object.fromEntries(overview.slice(1).map(r => [r[0], r[1]]));
const cards = [
  ["Flights", metrics["Flights"], "#,##0"], ["Average duration", metrics["Average flight duration minutes"], "0.0 \"min\""],
  ["Overnight flights", metrics["Overnight flights"], "#,##0"], ["Flight anomalies", metrics["Flight anomalies"], "#,##0"],
  ["Bookings", metrics["Bookings"], "#,##0"], ["Recorded payments", metrics["Recorded payment amount"], "#,##0.00"],
];
const cardCells = ["A4:B5", "C4:D5", "E4:F5", "G4:H5", "A7:D8", "E7:H8"];
for (const range of ["A4:B4", "A5:B5", "C4:D4", "C5:D5", "E4:F4", "E5:F5", "G4:H4", "G5:H5", "A7:D7", "A8:D8", "E7:H7", "E8:H8"]) dash.mergeCells(range);
for (let i = 0; i < cards.length; i++) {
  const [label, value, fmt] = cards[i];
  const [start] = cardCells[i].split(":");
  dash.getRange(cardCells[i]).format = { fill: "#F3F7FB", borders: { preset: "all", style: "thin", color: "#B8CCE4" }, verticalAlignment: "center" };
  dash.getRange(start).values = [[label]];
  dash.getRange(start).format = { font: { name: "Arial", size: 10, bold: true, color: "#17365D" }, horizontalAlignment: "center", verticalAlignment: "center" };
  const cell = dash.getRange(start).offset(1, 0);
  cell.values = [[num(value)]]; cell.format = { font: { name: "Arial", size: 16, bold: true, color: "#222222" }, numberFormat: fmt, horizontalAlignment: "center", verticalAlignment: "center" };
}
section(dash, "A10:H10"); dash.getRange("A10").values = [["Airline distribution"]];
dash.getRange("A11:D15").values = airlines.slice(0, 5).map((r, i) => i === 0 ? r : [r[0], num(r[1]), num(r[2]), num(r[3])]);
header(dash, "A11:D11"); dash.getRange("A11:D15").format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
dash.getRange("B12:D15").format.numberFormat = "#,##0.0";
const airlineChart = dash.charts.add("doughnut", dash.getRange("A11:B15"));
airlineChart.title = "Flights by airline"; airlineChart.titleTextStyle.typeface = "Arial"; airlineChart.titleTextStyle.fontSize = 12; airlineChart.legend = { position: "right", textStyle: { typeface: "Arial", fontSize: 9 } }; airlineChart.setPosition("E11", "K25");

routeSheet.getRange("A1").values = [["Route Performance"]]; routeSheet.getRange("A1").format = { font: { name: "Arial", size: 18, bold: true, color: "#17365D" } };
routeSheet.getRange("A2").values = [["Flight volume, average duration, and flagged flight records by route"]]; routeSheet.getRange("A2").format = { font: { name: "Arial", size: 10, italic: true, color: "#666666" } };
routeSheet.getRange(`A4:D${routes.length + 3}`).values = routes.map((r, i) => i === 0 ? r : [r[0], num(r[1]), num(r[2]), num(r[3])]);
header(routeSheet, "A4:D4"); routeSheet.getRange(`A4:D${routes.length + 3}`).format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
routeSheet.getRange(`B5:D${routes.length + 3}`).format.numberFormat = "#,##0.0";
const routeChart = routeSheet.charts.add("bar", routeSheet.getRange(`A4:B${routes.length + 3}`)); routeChart.title = "Flights by route"; routeChart.titleTextStyle.typeface = "Arial"; routeChart.titleTextStyle.fontSize = 12; routeChart.hasLegend = false; routeChart.setPosition("F4", "N23");

airlineSheet.getRange("A1").values = [["Airline Trends"]]; airlineSheet.getRange("A1").format = { font: { name: "Arial", size: 18, bold: true, color: "#17365D" } };
airlineSheet.getRange("A2").values = [["Flight count and average duration by airline"]]; airlineSheet.getRange("A2").format = { font: { name: "Arial", size: 10, italic: true, color: "#666666" } };
airlineSheet.getRange(`A4:D${airlines.length + 3}`).values = airlines.map((r, i) => i === 0 ? r : [r[0], num(r[1]), num(r[2]), num(r[3])]);
header(airlineSheet, "A4:D4"); airlineSheet.getRange(`A4:D${airlines.length + 3}`).format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
airlineSheet.getRange(`B5:D${airlines.length + 3}`).format.numberFormat = "#,##0.0";
const durationChart = airlineSheet.charts.add("bar", [airlineSheet.getRange(`A4:A${airlines.length + 3}`), airlineSheet.getRange(`C4:C${airlines.length + 3}`)]); durationChart.title = "Average duration by airline"; durationChart.titleTextStyle.typeface = "Arial"; durationChart.titleTextStyle.fontSize = 12; durationChart.hasLegend = false; durationChart.setPosition("F4", "N20");

anomalySheet.getRange("A1").values = [["Duration and Anomaly Insights"]]; anomalySheet.getRange("A1").format = { font: { name: "Arial", size: 18, bold: true, color: "#17365D" } };
anomalySheet.getRange("A2").values = [["Records flagged for short duration or arrival-date correction"]]; anomalySheet.getRange("A2").format = { font: { name: "Arial", size: 10, italic: true, color: "#666666" } };
anomalySheet.getRange(`A4:G${anomalies.length + 3}`).values = anomalies.map((r, i) => i === 0 ? r : [r[0], r[1], r[2], r[3], r[4], num(r[5]), r[6]]);
header(anomalySheet, "A4:G4"); anomalySheet.getRange(`A4:G${anomalies.length + 3}`).format.borders = { preset: "all", style: "thin", color: "#D9E2F3" }; anomalySheet.getRange(`F5:F${anomalies.length + 3}`).format.numberFormat = "#,##0";

dataSheet.getRange(`A1:O${flights.length}`).values = flights.map((r, i) => i === 0 ? r : r.map((v, j) => [7, 10].includes(j) ? num(v) : v));
header(dataSheet, "A1:O1"); dataSheet.freezePanes.freezeRows(1); dataSheet.getRange(`A1:O${flights.length}`).format.borders = { preset: "all", style: "thin", color: "#E7E6E6" };

for (const sheet of [dash, routeSheet, airlineSheet, anomalySheet, dataSheet]) { sheet.getUsedRange().format.autofitColumns(); sheet.getUsedRange().format.autofitRows(); }
dash.getRange("A:A").format.columnWidth = 20; dash.getRange("B:H").format.columnWidth = 14;
routeSheet.getRange("A:A").format.columnWidth = 20; anomalySheet.getRange("G:G").format.columnWidth = 42;

const check = await wb.inspect({ kind: "table", range: "Operations Summary!A1:H15", include: "values,formulas", tableMaxRows: 15, tableMaxCols: 8 });
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 50 }, summary: "final formula error scan" });
if (errors.ndjson && !errors.ndjson.includes("matches: 0")) console.log(errors.ndjson);
console.log(check.ndjson);
const preview = await wb.render({ sheetName: "Operations Summary", range: "A1:K25", scale: 2, format: "png" });
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
const xlsx = await SpreadsheetFile.exportXlsx(wb); await xlsx.save(fileURLToPath(outputPath));
