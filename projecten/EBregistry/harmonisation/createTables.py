"""
Maakt Tables.csv aan op basis van de schema-bestanden (EMX2-formaat) in harmonisation.zip.

Gebruik:
    python create_tables_csv.py                         # zoekt harmonisation.zip naast het script
    python create_tables_csv.py pad/naar/harmonisation.zip
    python create_tables_csv.py pad/naar/harmonisation.zip -o Tables.csv

Regels:
  - Elk schema-bestand (*.csv) is een resource (bestandsnaam zonder .csv).
  - Elke unieke tableName in zo'n bestand is een rij in Tables.csv (kolom "name").
  - table type: "Harmonised dataset" voor SESAR, anders "Collected dataset".
  - unit of observation: altijd "Patient".
  - number of rows: aantal rijen in het schema-bestand dat bij die tabel hoort
    (de tabel-definitieregel + alle kolomregels). Zie COUNT_ONLY_COLUMNS hieronder.
  - description: 'description' van de tabel-definitieregel; als die leeg is,
    wordt 'label' gebruikt (bij o.a. ADLAS/EPIC staat de omschrijving daar).
  - Alles wat verder in Tables.csv staat (label, keywords, versies) blijft leeg,
    mg_draft is altijd "false" -- precies zoals in het voorbeeld.
"""

import argparse
import csv
import io
import sys
import zipfile
from pathlib import Path

# --- Instellingen -----------------------------------------------------------

HARMONISED_RESOURCES = {"EB_registry"}          # alle andere resources zijn "Collected dataset"
UNIT_OF_OBSERVATION = "Patient"
COLLECTED = "Collected dataset"
HARMONISED = "Harmonised dataset"

# False: "number of rows" = alle rijen in het schema met die tableName
#        (definitieregel + kolommen).
# True : alleen de kolomregels tellen mee (dus het aantal kolommen).
COUNT_ONLY_COLUMNS = False

OUTPUT_COLUMNS = [
    "resource", "name", "label", "table type", "unit of observation",
    "keywords", "description", "number of rows",
    "since version", "until version", "mg_draft",
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


def tables_from_schema(resource: str, rows: list[dict]):
    """Een dict per tabel, in volgorde van eerste voorkomen in het bestand."""
    tables = {}
    for row in rows:
        name = (row.get("tableName") or "").strip()
        if not name:
            continue
        t = tables.setdefault(
            name, {"n_rows": 0, "n_cols": 0, "label": "", "description": ""}
        )
        t["n_rows"] += 1
        if (row.get("columnName") or "").strip():
            t["n_cols"] += 1
        else:  # tabel-definitieregel
            t["label"] = t["label"] or (row.get("label") or "").strip()
            t["description"] = t["description"] or (row.get("description") or "").strip()
    return tables


def build_records(zip_path: Path):
    records = []
    for resource, rows in read_schema_files(zip_path):
        table_type = HARMONISED if resource in HARMONISED_RESOURCES else COLLECTED
        for name, t in tables_from_schema(resource, rows).items():
            n = t["n_cols"] if COUNT_ONLY_COLUMNS else t["n_rows"]
            records.append({
                "resource": resource,
                "name": name,
                "label": "",
                "table type": table_type,
                "unit of observation": UNIT_OF_OBSERVATION,
                "keywords": "",
                "description": t["description"] or t["label"],
                "number of rows": n,
                "since version": "",
                "until version": "",
                "mg_draft": "false",
            })
    return records


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="Maak Tables.csv uit de schema's in een zip.")
    ap.add_argument("zip", nargs="?", default=str(here / "harmonisation.zip"),
                    help="pad naar harmonisation.zip")
    ap.add_argument("-o", "--output", default="Tables.csv", help="uitvoerbestand")
    args = ap.parse_args()

    zip_path = Path(args.zip)
    if not zip_path.exists():
        sys.exit(f"Zipbestand niet gevonden: {zip_path}")

    records = build_records(zip_path)
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        w.writeheader()
        w.writerows(records)

    per_resource = {}
    for r in records:
        per_resource[r["resource"]] = per_resource.get(r["resource"], 0) + 1
    print(f"{len(records)} tabellen weggeschreven naar {args.output}")
    for res, n in per_resource.items():
        print(f"  {res}: {n}")


if __name__ == "__main__":
    main()
