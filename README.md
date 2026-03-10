# AppSheet Export Parser

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://github.com/dwertz-at-blenko/appsheet-export-parser/actions/workflows/test.yml/badge.svg)](https://github.com/dwertz-at-blenko/appsheet-export-parser/actions/workflows/test.yml)

Parse any AppSheet documentation export (PDF) into structured JSON — schemas, relationships, actions, enums, computed fields, and more.

Built for **migration planning**: extract everything AppSheet knows about your app into a machine-readable format that LLMs, migration scripts, and ERD generators can consume.

## What It Extracts

- **Table schemas** — every column with type, key status, formula, description, and constraints
- **Relationships** — foreign keys via `Ref` columns, with parent/child mapping
- **Actions** — grouped by table, with action type and configuration
- **Slices** — filtered table views with row filter expressions
- **Computed fields** — columns driven by App Formulas or Initial Values
- **Enum fields** — columns with `EnumList` / `Enum` types and their valid values
- **Table classification** — auto-categorize tables as core (data) vs process (workflow)
- **Validation** — cross-check parsed counts against AppSheet's official header counts

## Pipeline

```
PDF ──→ Extract ──→ Parse ──→ Analyze ──→ JSON
         │           │          │           │
     raw text    sections   relationships  structured
     + header    schemas    computed fields  export
     counts      actions    enums            with
                 slices     classification   metadata
```

## Installation

```bash
pip install appsheet-export-parser
```

Or install from source:

```bash
git clone https://github.com/dwertz-at-blenko/appsheet-export-parser
cd appsheet-export-parser
pip install -e .
```

## Usage

### CLI

```bash
# Parse a PDF, write JSON output
appsheet-parse parse myapp-docs.pdf -o myapp.json

# Verbose mode — see pipeline progress
appsheet-parse parse myapp-docs.pdf -o myapp.json -v

# With custom table classification config
appsheet-parse parse myapp-docs.pdf -o myapp.json --config configs/myapp.yaml -v
```

### Python API

```python
from appsheet_export_parser.parser import parse_pdf

# Parse and get the result dict
export = parse_pdf("myapp-docs.pdf", output_path="myapp.json", verbose=True)

# Access parsed data
for table, columns in export["schemas"].items():
    print(f"{table}: {len(columns)} columns")

for rel in export["relationships"]:
    print(f"{rel['child_table']}.{rel['child_column']} → {rel['parent_table']}")
```

## Output Format

The JSON output follows schema version `1.0.0`:

```json
{
  "schema_version": "1.0.0",
  "metadata": {
    "app_name": "My App",
    "parser_version": "1.0.0",
    "summary": {
      "total_tables": 24,
      "total_columns": 312,
      "total_relationships": 18,
      "total_actions": 45
    }
  },
  "core_table_names": ["Orders", "Customers", "Products"],
  "process_table_names": ["Process for Order"],
  "schemas": {
    "Orders": [
      {
        "name": "OrderID",
        "type": "Text",
        "key": true,
        "formula": "",
        "description": "Unique order identifier"
      }
    ]
  },
  "relationships": [
    {
      "parent_table": "Customers",
      "child_table": "Orders",
      "child_column": "CustomerRef",
      "relationship_type": "one_to_many"
    }
  ],
  "computed_fields": [],
  "enum_fields": [],
  "actions": [],
  "slices": []
}
```

## Claude Code Skill

This repo includes a Claude Code skill plugin for interactive parsing sessions:

```
/parse-appsheet ~/Downloads/myapp-docs.pdf
```

The skill runs the parser, validates output, and presents results conversationally.

## Customization

The parser works for **any** AppSheet app out of the box. To customize table classification, ERD colors, or skill behavior for your specific app, see the [Fork Guide](FORK-GUIDE.md).

## Development

```bash
git clone https://github.com/dwertz-at-blenko/appsheet-export-parser
cd appsheet-export-parser
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=appsheet_export_parser
```

## License

[MIT](LICENSE)
