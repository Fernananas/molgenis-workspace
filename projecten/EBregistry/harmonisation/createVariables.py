#!/usr/bin/env python3
"""
Maakt Variables.csv aan op basis van de schema-bestanden (EMX2-formaat) in harmonisation.zip.

Gebruik:
    python create_variables_csv.py                         # zoekt harmonisation.zip naast het script
    python create_variables_csv.py pad/naar/harmonisation.zip
    python create_variables_csv.py pad/naar/harmonisation.zip -o Variables.csv

Regels:
  - Elk schema-bestand (*.csv) is een resource (bestandsnaam zonder .csv).
  - Elke regel met een columnName is een variabele:
        resource = bestandsnaam, table = tableName, name = columnName
  - Uit het schema worden daarnaast overgenomen:
        label              <- label
        description        <- description
        format             <- columnType (vertaald via FORMAT_MAP; leeg type = "string",
                              de EMX2-standaard)
        ontology term URI  <- semantics (ongewijzigd overgenomen)
  - mg_draft is altijd "false".
  - Alle andere kolommen (example values, keywords, mappings, ...) zijn handmatig werk
    en blijven leeg.
"""

import argparse
import csv
import io
import sys
import zipfile
from pathlib import Path

# --- Instellingen -----------------------------------------------------------

# EMX2 'heading'-regels zijn alleen kopjes in een formulier, geen echte variabelen.
# Zet op True om ze toch mee te nemen.
INCLUDE_HEADINGS = False

# Vertaling van EMX2 columnType naar de 'format'-waarde in Variables.csv.
# Een leeg columnType betekent in EMX2 "string". Niet-genoemde types worden
# ongewijzigd overgenomen. Pas deze tabel gerust aan.
FORMAT_MAP = {
    "": "string",
    "string": "string",
    "text": "string",
    "auto_id": "string",
    "email": "string",
    "hyperlink": "string",
    "select": "categorical",
    "multiselect": "categorical",
    "radio": "string",
    "ref": "categorical",
    "ref_array": "categorical",
    "ontology": "categorical",
    "ontology_array": "categorical",
    "string_array": "string",
    "text_array": "text",
    "int": "integer",
    "long": "integer",
    "decimal": "decimal",
    "bool": "binary",
    "date": "date",
    "datetime": "datetime",
    "period": "date",
    "file": "file",
}

OUTPUT_COLUMNS = [
    "resource", "table", "name",
    "useExternalDefinition.resource", "useExternalDefinition.table", "useExternalDefinition.name",
    "label", "description", "original language description", "format", "unit",
    "ontology term URI", "since version", "until version",
    "repeat unit", "repeat min", "repeat max", "example values",
    "permitted values.resource", "permitted values.table",
    "permitted values.variable", "permitted values.value",
    "keywords", "generated_keywords", "vocabularies", "notes", "collection event",
    "reused in resources.resource", "reused in resources.variable.resource",
    "reused in resources.variable.table", "reused in resources.variable.name",
    "mappings.source", "mappings.source table", "mappings.target",
    "mappings.target table", "mappings.target variable", "mappings.repeats",
    "mg_draft",
]


# --- Logica -----------------------------------------------------------------

def read_schema_files(zip_path: Path):
    """Geeft (resource, lijst-met-dict-rijen) per schema-bestand in de zip."""
    with zipfile.ZipFile(zip_path) as zf:
        entries = []
        for info in zf.infolist():
            p = Path(info.filename)
            if info.is_dir() or p.suffix.lower() != ".csv":
                continue
            if "__MACOSX" in p.parts or p.name.startswith("._"):
                continue                      # macOS-rommel
            if len(p.parts) > 2:
                continue                      # submappen (bv. de voorbeeldmap) overslaan
            entries.append(info)

        for info in sorted(entries, key=lambda i: Path(i.filename).stem.lower()):
            text = zf.read(info).decode("utf-8-sig")
            rows = list(csv.DictReader(io.StringIO(text, newline="")))
            yield Path(info.filename).stem, rows


def build_records(zip_path: Path):
    records = []
    skipped_headings = 0
    for resource, rows in read_schema_files(zip_path):
        for row in rows:
            table = (row.get("tableName") or "").strip()
            name = (row.get("columnName") or "").strip()
            if not table or not name:
                continue                      # tabel-definitieregel, geen variabele

            col_type = (row.get("columnType") or "").strip()
            if col_type == "heading" and not INCLUDE_HEADINGS:
                skipped_headings += 1
                continue

            rec = {c: "" for c in OUTPUT_COLUMNS}
            rec.update({
                "resource": resource,
                "table": table,
                "name": name,
                "label": (row.get("label") or "").strip(),
                "description": (row.get("description") or "").strip(),
                "format": FORMAT_MAP.get(col_type, col_type),
                "ontology term URI": (row.get("semantics") or "").strip(),
                "mg_draft": "false",
            })
            records.append(rec)
    return records, skipped_headings


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="Maak Variables.csv uit de schema's in een zip.")
    ap.add_argument("zip", nargs="?", default=str(here / "harmonisation.zip"),
                    help="pad naar harmonisation.zip")
    ap.add_argument("-o", "--output", default="Variables.csv", help="uitvoerbestand")
    args = ap.parse_args()

    zip_path = Path(args.zip)
    if not zip_path.exists():
        sys.exit(f"Zipbestand niet gevonden: {zip_path}")

    records, skipped = build_records(zip_path)
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        w.writeheader()
        w.writerows(records)

    per_resource = {}
    for r in records:
        per_resource[r["resource"]] = per_resource.get(r["resource"], 0) + 1
    print(f"{len(records)} variabelen weggeschreven naar {args.output}")
    for res, n in per_resource.items():
        print(f"  {res}: {n}")
    if skipped:
        print(f"({skipped} 'heading'-regels overgeslagen; zie INCLUDE_HEADINGS)")


if __name__ == "__main__":
    main()
