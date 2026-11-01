import csv
import re
from pathlib import Path


def sanitize_filename(value: str) -> str:
    """Create safe ASCII filename stem from ontology name."""
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "", value or "")
    return cleaned or "UnknownOntology"


def build_ontology_files() -> None:
    base_dir = Path(__file__).resolve().parent
    input_path = base_dir / "data/input" / "optionsEB.csv"
    output_dir = base_dir / "data/output"
    output_dir.mkdir(parents=True, exist_ok=True)

    grouped: dict[str, list[tuple[str, str]]] = {}

    with input_path.open("r", encoding="utf-8-sig", newline="") as src:
        reader = csv.DictReader(src)
        for row in reader:
            name = (row.get("name") or "").strip()
            label = (row.get("label") or "").strip()
            ontology = (row.get("ONTOLOGIES") or "").strip()

            # Skip blank separators and rows without ontology/value payload.
            if not ontology or not name or not label:
                continue

            grouped.setdefault(ontology, []).append((name, label))

    created = 0
    for ontology, options in sorted(grouped.items(), key=lambda item: item[0].lower()):
        filename = f"{sanitize_filename(ontology)}.csv"
        target = output_dir / filename

        # Keep first occurrence order, drop accidental duplicates.
        seen = set()
        unique_options = []
        for key, text in options:
            pair = (key, text)
            if pair in seen:
                continue
            seen.add(pair)
            unique_options.append(pair)

        with target.open("w", encoding="utf-8", newline="") as dst:
            writer = csv.writer(dst)
            writer.writerow(["name", "label", "ONTOLOGIES"])
            for key, text in unique_options:
                writer.writerow([key, text, ontology])

        created += 1

    print(f"Created {created} ontology file(s) in: {output_dir}")


if __name__ == "__main__":
    build_ontology_files()
