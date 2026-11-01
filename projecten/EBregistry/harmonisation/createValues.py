#!/usr/bin/env python3
"""
Maakt VariableValues.csv voor het EB_registry schema, wanneer de ontologieën
zelf in het schema zitten, maar de ontologiedata in een aparte map staat.

Gebruik:
    python create_variable_values_csv.py
    python create_variable_values_csv.py harmonisation EBontologies -o VariableValues.csv

Beide bronnen mogen een map of een zip zijn. Standaard wordt naast het script
gezocht naar harmonisation(.zip) en EBontologies(.zip).

Regels:
  - Het schema (EB_registry.csv) wordt ALLEEN in de harmonisation-bron gezocht.
  - De ontologiedata (<tabelnaam>.csv) wordt ALLEEN in de EBontologies-bron gezocht.
  - Een variabele kwalificeert als columnType categorisch is
    (ontology, ontology_array, ref, ref_array, select, multiselect, radio)
    EN refSchema leeg is (of gelijk aan EB_registry)
    EN refTable een ontologie-tabel is (tableType = ONTOLOGIES in het schema).
    Staan er geen ONTOLOGIES-tabellen in het schema, dan telt elke refTable
    waarvoor een csv in de EBontologies-bron bestaat.
  - Elke rij wordt een rij in VariableValues (zie OUTPUT_COLUMNS).
  - Ontologieën met meer dan MAX_ROWS rijen worden overgeslagen.
"""

import argparse
import csv
import io
import sys
import zipfile
from pathlib import Path

# --- Instellingen -----------------------------------------------------------

SCHEMA_NAME = "EB_registry"
MAX_ROWS = 450
CATEGORICAL_TYPES = {
    "ontology", "ontology_array", "ref", "ref_array",
    "select", "multiselect", "radio",
}
ONTOLOGY_TABLE_TYPE = "ONTOLOGIES"

OUTPUT_COLUMNS = [
    "resource", "table", "variable", "value", "label", "order",
    "is missing", "ontology term URI", "since version", "until version",
]


# --- Hulpfuncties -----------------------------------------------------------

def read_csv_text(text: str):
    return list(csv.DictReader(io.StringIO(text.lstrip("\ufeff"), newline="")))


def _skip(p: Path) -> bool:
    return "__MACOSX" in p.parts or p.name.startswith("._")


def iter_csv_files(source: Path):
    """Levert (pad, tekst) voor elk csv-bestand in een zip of map."""
    if source.is_dir():
        for p in sorted(source.rglob("*.csv")):
            if not _skip(p):
                yield p, p.read_text(encoding="utf-8")
    else:
        with zipfile.ZipFile(source) as zf:
            for info in zf.infolist():
                p = Path(info.filename)
                if info.is_dir() or p.suffix.lower() != ".csv" or _skip(p):
                    continue
                yield p, zf.read(info).decode("utf-8")


def default_source(here: Path, name: str) -> Path:
    """Zoekt naast het script naar <name>/, <name>.zip of <name>*.zip."""
    for cand in (here / name, here / f"{name}.zip"):
        if cand.exists():
            return cand
    return next(here.glob(f"{name}*.zip"), here / name)


def load_schema(source: Path):
    """Alle schema-rijen uit EB_registry.csv in de harmonisation-bron."""
    for p, text in iter_csv_files(source):
        if p.name == f"{SCHEMA_NAME}.csv":
            return read_csv_text(text)
    sys.exit(f"{SCHEMA_NAME}.csv niet gevonden in {source}")


def load_ontology_data(source: Path):
    """dict: bestandsnaam zonder .csv -> lijst rij-dicts, uit de EBontologies-bron."""
    data = {}
    for p, text in iter_csv_files(source):
        data.setdefault(p.stem, read_csv_text(text))
    return data


def find_ontology_tables(schema_rows, onts):
    """Tabelnamen met tableType ONTOLOGIES; anders fallback op beschikbare csv's."""
    tables = {
        (r.get("tableName") or "").strip()
        for r in schema_rows
        if (r.get("tableType") or "").strip().upper() == ONTOLOGY_TABLE_TYPE
    }
    return tables or set(onts)


def load_schema_variables(schema_rows, ontology_tables):
    """(table, column, refTable) voor elke kwalificerende variabele, in bestandsvolgorde."""
    result = []
    for r in schema_rows:
        col = (r.get("columnName") or "").strip()
        if not col:
            continue  # tabel-rij, geen kolom
        if (r.get("columnType") or "").strip() not in CATEGORICAL_TYPES:
            continue
        if (r.get("refSchema") or "").strip() not in ("", SCHEMA_NAME):
            continue
        ref_table = (r.get("refTable") or "").strip()
        if ref_table not in ontology_tables:
            continue
        result.append(((r.get("tableName") or "").strip(), col, ref_table))
    return result


def ontology_orders(rows):
    """Expliciete 'order' als ELKE rij er een heeft, anders 1..n op bestandspositie."""
    explicit = [(r.get("order") or "").strip() for r in rows]
    if rows and all(explicit):
        return explicit
    return [str(i) for i in range(1, len(rows) + 1)]


# --- Main -------------------------------------------------------------------

def build_records(harmonisation: Path, ontologies: Path):
    schema_rows = load_schema(harmonisation)
    onts = load_ontology_data(ontologies)
    ontology_tables = find_ontology_tables(schema_rows, onts)
    variables = load_schema_variables(schema_rows, ontology_tables)

    records, skipped_big, missing_files, empty = [], {}, set(), set()
    for table, column, ref_table in variables:
        rows = onts.get(ref_table)
        if rows is None:
            missing_files.add(ref_table)
            continue
        if len(rows) > MAX_ROWS:
            skipped_big.setdefault(ref_table, []).append(f"{table}.{column}")
            continue
        if not rows:
            empty.add(ref_table)
            continue
        for order, r in zip(ontology_orders(rows), rows):
            records.append({
                "resource": SCHEMA_NAME,
                "table": table,
                "variable": column,
                "value": (r.get("name") or "").strip(),
                "label": (r.get("label") or "").strip(),
                "order": order,
                "is missing": "",
                "ontology term URI": (r.get("ontologyTermURI") or "").strip(),
                "since version": "",
                "until version": "",
            })
    return records, len(variables), skipped_big, missing_files, empty


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="Maak VariableValues.csv voor EB_registry.")
    ap.add_argument("harmonisation", nargs="?", default=str(default_source(here, "harmonisation")),
                    help="map of zip met het schema (EB_registry.csv)")
    ap.add_argument("ontologies", nargs="?", default=str(default_source(here, "EBontologies")),
                    help="map of zip met de ontologie-csv's")
    ap.add_argument("-o", "--output", default="VariableValues.csv")
    args = ap.parse_args()

    for p in (args.harmonisation, args.ontologies):
        if not Path(p).exists():
            sys.exit(f"Bestand of map niet gevonden: {p}")

    records, n_vars, skipped_big, missing, empty = build_records(
        Path(args.harmonisation), Path(args.ontologies)
    )

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        w.writeheader()
        w.writerows(records)

    with_values = len({(r["table"], r["variable"]) for r in records})
    n_skipped_vars = sum(len(v) for v in skipped_big.values())
    print(f"{len(records)} waarde-rijen geschreven naar {args.output}")
    print(f"{n_vars} kwalificerende variabelen: {with_values} met waarden, "
          f"{n_skipped_vars} overgeslagen (ontologie > {MAX_ROWS} rijen), "
          f"{n_vars - with_values - n_skipped_vars} zonder waarden (leeg of ontbrekend bestand)")
    if skipped_big:
        print(f"Overgeslagen ontologieën (> {MAX_ROWS} rijen): " + ", ".join(sorted(skipped_big)))
    if empty:
        print("Lege ontologiebestanden: " + ", ".join(sorted(empty)))
    if missing:
        print("Ontologiebestand niet gevonden in EBontologies: " + ", ".join(sorted(missing)))


if __name__ == "__main__":
    main()