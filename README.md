# AppSheet Export Parser

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://github.com/dwertz-at-blenko/appsheet-export-parser/actions/workflows/test.yml/badge.svg)](https://github.com/dwertz-at-blenko/appsheet-export-parser/actions/workflows/test.yml)

Parse any AppSheet documentation export (PDF) into structured, machine-readable JSON. Built to help teams migrate away from AppSheet to platforms like Retool, Postgres, Supabase, or whatever comes next.

## Why This Exists

AppSheet is a Google product that feels abandoned. The dev team shows no sign of life. Feature requests sit for years. The community forum is full of unanswered questions. Critical bugs go unacknowledged. Meanwhile, Google keeps shipping new AI products and AppSheet sits there, frozen in time, running business-critical operations for companies that trusted the platform.

If you've built something real on AppSheet — 50+ tables, thousands of columns, hundreds of actions, complex business logic encoded in formulas — you're stuck. There's no export button. No migration tool. No API that gives you your own schema. The only thing AppSheet offers is "Generate Documentation," which dumps a PDF that can run thousands of pages. Good luck reading that.

**This parser exists because migration shouldn't require manually transcribing a 2,700-page PDF.**

It reads that documentation export and extracts everything AppSheet knows about your app — every table, column, relationship, action, formula, enum, and constraint — into clean, structured JSON. From there, you can feed it to an LLM for migration planning, generate DDL for Postgres or MySQL, build ERDs, or write automated migration scripts. The hard part (getting your data model *out* of AppSheet) is solved.

We built this for our own migration — a 55-table ERP with 3,044 columns and 293 actions — and we're open-sourcing it because nobody should have to do this by hand.

## The Technical Problem

AppSheet's "Generate Documentation" PDF is not designed for machine consumption. It contains every table, column, action, slice, and formula in your app, but the format is inconsistent: JSON blobs break across page boundaries, fields are context-dependent, and there's no stable structure to parse against. A 55-table app produces a 2,718-page PDF with over 3 million characters of raw text.

This parser handles all of that — page-break repair, broken JSON reconstruction, multi-line formula extraction, smart relationship inference — and validates its own output against AppSheet's official counts to prove nothing was lost.

## Demo

```
$ appsheet-parse parse myapp-docs.pdf -o myapp.json -v

Extracting text from myapp-docs.pdf...
  3,111,819 characters, 2718 pages
  Header: 55 tables, 3044 columns, 293 actions
  Cleaned to 279,186 lines
Finding sections...
  Schema blocks: 55
Parsing schemas...
  55 tables, 3044 columns
Parsing actions...
  293 actions
Parsing slices...
  36 slices
Analyzing relationships...
  99 relationships
Extracting computed fields...
  797 computed fields
Extracting enum fields...
  41 enum fields
Validating against header counts...
  [OK] Tables: 55/55
  [OK] Columns: 3044/3044 -- EXACT MATCH
  [OK] Actions: 293/293
  [OK] Slices: 36/36

Parsed successfully!
  App: BERP V1.7 - Live
  Tables: 55 (20 core, 33 process)
  Columns: 3044
  Relationships: 99
  Actions: 293
  Output: myapp.json
```

The parser validates its own output against the official counts in the PDF header. **EXACT MATCH** means every table, column, action, and slice was captured — nothing lost.

## What It Extracts

**Per column** (up to 25+ fields each):

| Field | Example |
|-------|---------|
| `name`, `type` | `"UserID"`, `"Email"` |
| `is_key`, `is_label` | Key and label column flags |
| `app_formula` | `=CONCATENATE([Last Name], ", ", [First Name])` |
| `initial_value` | Default value expressions |
| `referenced_table` | Foreign key target (from `Ref` columns) |
| `enum_values` | `["Pending", "In Progress", "Complete"]` |
| `valid_if`, `show_if`, `editable_if` | Constraint expressions |
| `description`, `display_name` | Human-readable metadata |
| `read_only`, `hidden`, `searchable`, `sensitive` | Boolean flags |

**Across the app:**

- **Table schemas** — every column with full metadata
- **Relationships** — foreign keys inferred from `Ref` columns, with smart matching (handles naming conventions, plural/singular, underscores)
- **Actions** — grouped by table, with type (`COMPOSITE`, `SET_VALUES`, etc.), conditions, and full properties
- **Slices** — filtered table views with row filter expressions and column lists
- **Computed fields** — columns driven by App Formulas, Initial Values, or Spreadsheet Formulas
- **Enum fields** — columns with `Enum`/`EnumList` types and their valid values
- **Table classification** — auto-categorize tables as core (business data) vs process (automation artifacts)
- **Official counts** — AppSheet's own header counts, preserved for validation

## Architecture

```
src/appsheet_export_parser/
├── extract/          # Stage 1: PDF → raw text
│   ├── pdf.py        #   pdftotext wrapper
│   ├── cleaner.py    #   Strip page breaks, headers, noise
│   └── header.py     #   Parse official counts from doc header
├── parse/            # Stage 2: Text → structured sections
│   ├── section_finder.py  #   Locate schema/action/slice boundaries
│   ├── schema_parser.py   #   Parse table → column definitions
│   ├── action_parser.py   #   Parse action definitions
│   ├── slice_parser.py    #   Parse slice definitions
│   ├── field_parser.py    #   Key-value field extraction
│   └── json_repair.py     #   Fix broken JSON in Type Qualifiers
├── analyze/          # Stage 3: Cross-table analysis
│   ├── relationships.py   #   Infer Ref relationships + smart matching
│   ├── computed_fields.py #   Extract formula-driven columns
│   ├── enums.py           #   Extract enumerated value columns
│   ├── classifier.py      #   Core vs process table classification
│   └── validator.py       #   Validate parsed vs official counts
├── generate/         # Stage 4: Build canonical output
│   └── json_output.py    #   Versioned JSON export (schema v1.0.0)
├── models/           # Pydantic models for all data types
├── parser.py         # Top-level orchestrator
└── cli.py            # Typer CLI
```

The pipeline runs in four stages: **Extract** (PDF → cleaned text) → **Parse** (text → sections and schemas) → **Analyze** (cross-table relationships, computed fields, enums) → **Generate** (canonical versioned JSON).

## Installation

**Prerequisite**: `pdftotext` (from poppler-utils):

```bash
# Ubuntu/Debian
sudo apt install poppler-utils

# macOS
brew install poppler
```

Then install the parser:

```bash
pip install appsheet-export-parser
```

Or from source:

```bash
git clone https://github.com/dwertz-at-blenko/appsheet-export-parser
cd appsheet-export-parser
pip install -e .
```

## Usage

### CLI

```bash
# Basic parse
appsheet-parse parse myapp-docs.pdf -o myapp.json

# Verbose — see pipeline progress and validation
appsheet-parse parse myapp-docs.pdf -o myapp.json -v

# With custom table classification config
appsheet-parse parse myapp-docs.pdf -o myapp.json --config configs/myapp.yaml -v
```

### Python API

```python
from appsheet_export_parser.parser import parse_pdf

export = parse_pdf("myapp-docs.pdf", output_path="myapp.json", verbose=True)

# Iterate schemas
for table, columns in export["schemas"].items():
    key_cols = [c["name"] for c in columns if c.get("is_key")]
    print(f"{table}: {len(columns)} columns, keys={key_cols}")

# Walk relationships
for rel in export["relationships"]:
    print(f"{rel['from_table']}.{rel['from_column']} → {rel['to_table']}")

# Find all enums
for enum in export["enum_fields"]:
    print(f"{enum['table']}.{enum['column']}: {enum['values']}")
```

## Output Format

Schema version `1.0.0`. Every field shown below is real, from an actual parse:

```json
{
  "schema_version": "1.0.0",
  "metadata": {
    "app_name": "BERP V1.7 - Live",
    "version": "5.001266",
    "generated": "2026-03-10",
    "parser_version": "1.0.0",
    "source_pages": 2718,
    "summary": {
      "total_tables": 55,
      "core_tables": 20,
      "process_tables": 33,
      "total_columns": 3044,
      "total_actions": 293,
      "total_slices": 36,
      "total_relationships": 99,
      "total_computed_fields": 797,
      "total_enum_fields": 41
    },
    "official_counts": {
      "tables": 55,
      "columns": 3044,
      "actions": 293,
      "slices": 36,
      "views": 153,
      "format_rules": 33
    }
  },
  "core_table_names": ["Employee", "Work_Card", "Shops", "..."],
  "process_table_names": ["Process for Checkin", "Checkin Output", "..."],
  "schemas": {
    "Employee": [
      {
        "name": "UserID",
        "type": "Email",
        "is_key": true,
        "searchable": true,
        "sensitive": true,
        "display_name": "=\"Email\""
      },
      {
        "name": "Combined Name",
        "type": "Name",
        "is_label": true,
        "initial_value": "=CONCATENATE([Last Name], \", \", [First Name])"
      }
    ]
  },
  "relationships": [
    {
      "from_table": "Grinding",
      "from_column": "Work_Card_ID",
      "to_table": "Work_Card",
      "referenced_type": "Text"
    }
  ],
  "actions": [
    {
      "name": "Copy and Edit",
      "table": "Work_Card",
      "action_type": "COMPOSITE",
      "modifies_data": true,
      "condition": "=IF(OR(ANY(SELECT(Employee[Role], ...)) = 'Admin', ...), TRUE, FALSE)"
    }
  ],
  "enum_fields": [
    {
      "table": "Grinding",
      "column": "Grinding_Status",
      "type": "Enum",
      "values": ["1 - Pending Work", "2 - Work in Progress", "3 Partial Work Complete", "4 - Work Complete"]
    }
  ],
  "computed_fields": [],
  "slices": []
}
```

## Configuration

### Table Classification

Create a YAML config to control how tables are categorized:

```yaml
table_classification:
  core:
    - Employee
    - Orders
    - Products
  process:
    - "Process for *"     # Wildcard matching
    - "* Output"
  skip:
    - Home
    - Dashboard

migration_target: postgres
```

Without a config, the parser auto-classifies using naming heuristics (tables matching `Process for *` or `* Output` patterns are marked as process tables).

### ERD Domain Colors

Group tables into color-coded domains for ERD generation:

```yaml
app_name: "My App"
domains:
  Sales:
    color: "#1565C0"
    fill: "#E3F2FD"
    tables: [Orders, Customers, Products]
  HR:
    color: "#2E7D32"
    fill: "#E8F5E9"
    tables: [Employee, Department]
```

## Claude Code Skill

This repo includes a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill plugin for interactive parsing:

```bash
# Install the skill plugin
claude plugin install ./skill

# Then use it in any session
/parse-appsheet ~/Downloads/myapp-docs.pdf
```

The skill handles prerequisites, runs the parser, presents a validation summary, and offers next steps (inspect tables, view relationships, etc.).

## Customization

The parser works for **any** AppSheet app out of the box. To customize table classification, ERD domain colors, or skill behavior for your specific app, see the **[Fork Guide](FORK-GUIDE.md)** — it's designed so forks pull upstream parser improvements without merge conflicts.

## Development

```bash
git clone https://github.com/dwertz-at-blenko/appsheet-export-parser
cd appsheet-export-parser
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run unit tests (no fixtures needed)
pytest tests/ --ignore=tests/test_integration.py -v

# Run integration tests (requires a PDF in tests/fixtures/)
pytest tests/test_integration.py -v

# Type checking
mypy src/
```

Integration tests require an AppSheet documentation PDF in `tests/fixtures/`. They skip gracefully when the fixture is absent (CI runs unit tests only).

## License

[MIT](LICENSE)
