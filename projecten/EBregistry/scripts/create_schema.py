import csv
import re
from pathlib import Path


def to_camel_case(text: str, max_len: int = 255) -> str:
    """Convert label text to safe camelCase with only [A-Za-z0-9_]."""
    if not text:
        return ""

    normalized = re.sub(r"[^A-Za-z0-9_]+", " ", text).strip()
    if not normalized:
        return ""

    parts = [p for p in normalized.split() if p]
    first = parts[0].lower()
    rest = "".join(p[:1].upper() + p[1:].lower() for p in parts[1:])
    value = (first + rest)[:max_len]
    return value


def map_column_type(datatype: str) -> str:
    dt = (datatype or "").strip().lower()
    if not dt:
        return "string"
    if "auto-id" in dt or "auto_id" in dt:
        return "auto_id"
    if "date" in dt:
        return "date"
    if "bool" in dt:
        return "bool"
    if "int" in dt:
        return "int"
    if "text" in dt:
        return "text"
    if "string" in dt:
        return "string"
    if "ref_array" in dt:
        return "ref_array"
    if "ref" in dt:
        return "ref"
    return "string"


def required_value(raw: str) -> str:
    r = (raw or "").strip().lower()
    return "true" if r == "yes" else ""


def build_schema() -> None:
    base_dir = Path(__file__).resolve().parent
    input_dir = base_dir / "data/input"
    output_dir = base_dir / "data/output"
    output_dir.mkdir(parents=True, exist_ok=True)

    core_fields_path = input_dir / "core_fields.csv"
    target_path = output_dir / "EB_registry_schema.csv"

    schema_header = [
        "tableName",
        "tableExtends",
        "tableType",
        "columnName",
        "formLabel",
        "columnType",
        "key",
        "required",
        "readonly",
        "refSchema",
        "refTable",
        "refLink",
        "refBack",
        "refLabel",
        "defaultValue",
        "validation",
        "visible",
        "computed",
        "semantics",
        "profiles",
        "label",
        "description",
    ]

    table_map = {
        "individuals": "Individuals",
        "biopsy": "Biopsies",
        "biopsies": "Biopsies",
        "variants": "Variants",
    }

    rows_out = []
    seen_fields = set()
    inserted_headings = set()

    with core_fields_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_label = (row.get("label") or "").strip()
            raw_description = (row.get("description") or "").strip()
            raw_section = (row.get("section") or "").strip()
            raw_table = (row.get("table") or "").strip()
            raw_datatype = (row.get("datatype") or "").strip()
            raw_required = (row.get("required") or "").strip()

            if not raw_label:
                continue

            table_name = table_map.get(raw_table.lower(), raw_table.title() if raw_table else "Individuals")
            column_name = to_camel_case(raw_label)
            if not column_name:
                continue

            section_key = (table_name, raw_section.lower())
            if raw_section and section_key not in inserted_headings:
                heading_name = to_camel_case(raw_section)
                if heading_name:
                    rows_out.append(
                        {
                            "tableName": table_name,
                            "tableExtends": "",
                            "tableType": "",
                            "columnName": heading_name,
                            "formLabel": raw_section,
                            "columnType": "heading",
                            "key": "",
                            "required": "",
                            "readonly": "",
                            "refSchema": "",
                            "refTable": "",
                            "refLink": "",
                            "refBack": "",
                            "refLabel": "",
                            "defaultValue": "",
                            "validation": "",
                            "visible": "",
                            "computed": "",
                            "semantics": "",
                            "profiles": "",
                            "label": raw_section,
                            "description": f"Section heading: {raw_section}",
                        }
                    )
                    inserted_headings.add(section_key)

            field_key = (table_name, column_name)
            if field_key in seen_fields:
                continue
            seen_fields.add(field_key)

            rows_out.append(
                {
                    "tableName": table_name,
                    "tableExtends": "",
                    "tableType": "",
                    "columnName": column_name,
                    "formLabel": raw_label,
                    "columnType": map_column_type(raw_datatype),
                    "key": "",
                    "required": required_value(raw_required),
                    "readonly": "",
                    "refSchema": "",
                    "refTable": "",
                    "refLink": "",
                    "refBack": "",
                    "refLabel": "",
                    "defaultValue": "",
                    "validation": "",
                    "visible": "",
                    "computed": "",
                    "semantics": "",
                    "profiles": "",
                    "label": raw_label,
                    "description": raw_description,
                }
            )

    with target_path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=schema_header)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Schema generated: {target_path}")
    print(f"Rows written: {len(rows_out)}")


if __name__ == "__main__":
    build_schema()
