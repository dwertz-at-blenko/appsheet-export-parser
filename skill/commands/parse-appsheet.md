---
description: Parse an AppSheet documentation export (PDF or URL) into structured JSON
argument-hint: <pdf-path-or-url>
allowed-tools: [Bash, Read, Glob, Grep, Write, Edit]
---

# /parse-appsheet -- Parse AppSheet Documentation

Parse an AppSheet application's documentation export into structured JSON containing tables, columns, relationships, actions, slices, computed fields, and enum fields.

## Arguments

`$ARGUMENTS` should be one of:
- A **file path** to an AppSheet documentation PDF (e.g., `~/Downloads/myapp-docs.pdf`)
- A **URL** to an AppSheet live documentation page (Phase 2 — not yet supported)

If no argument is provided, ask the user for the path to their AppSheet documentation PDF.

## Prerequisites (run silently before parsing)

1. Check if the library is installed:
   ```bash
   python3 -c "import appsheet_export_parser" 2>/dev/null
   ```

2. If not installed, install it:
   ```bash
   pip install appsheet-export-parser
   ```
   If pip install fails (no PyPI release yet), install from source:
   ```bash
   pip install -e /path/to/appsheet-export-parser
   ```

3. Verify `pdftotext` is available (required for PDF mode):
   ```bash
   which pdftotext
   ```
   If missing, inform the user:
   ```
   pdftotext not found. Install poppler-utils:
     Ubuntu/Debian: sudo apt install poppler-utils
     macOS: brew install poppler
   ```

## Parsing Steps

### Step 1: Validate Input

- If `$ARGUMENTS` starts with `http`, inform the user that URL mode is not yet supported and ask for a PDF path instead.
- If `$ARGUMENTS` is a file path, verify it exists.
- If the path uses `~`, expand it.

### Step 2: Run the Parser

```bash
python3 -c "
from appsheet_export_parser.parser import parse_pdf
result = parse_pdf(
    '$ARGUMENTS',
    output_path='$(dirname $ARGUMENTS)/$(basename $ARGUMENTS .pdf)-parsed.json',
    verbose=True,
)
"
```

If the user has an app config YAML (table classifications), pass it:
```bash
python3 -c "
from appsheet_export_parser.parser import parse_pdf
result = parse_pdf(
    '$ARGUMENTS',
    output_path='output.json',
    app_config_path='configs/myapp-app-config.yaml',
    verbose=True,
)
"
```

### Step 3: Present Results

After parsing completes, present a summary table:

```
| Metric        | Parsed | Header | Status |
|---------------|--------|--------|--------|
| Tables        | N      | N      | OK/WARN |
| Columns       | N      | N      | OK/WARN |
| Actions       | N      | N      | OK/WARN |
| Slices        | N      | N      | OK/WARN |
| Relationships | N      | -      | -      |
| Computed      | N      | -      | -      |
| Enum Fields   | N      | -      | -      |
```

Explain any discrepancies:
- **Tables**: If parsed < header, the difference is usually Process/Output tables (automation artifacts, not data tables).
- **Actions**: Cross-table duplicates are common. AppSheet repeats actions across related tables.
- **Columns**: Should be an EXACT MATCH. If not, there's a parsing issue.

### Step 4: Offer Next Steps

Ask the user what they'd like to do next:

1. **View table list** — Show all parsed tables with column counts
2. **Inspect a table** — Show columns, types, and relationships for a specific table
3. **Generate ERD** — Create a relationship diagram (requires graphviz, Phase 2)
4. **Generate DDL** — Create SQL schema for migration (Phase 2)
5. **Migration planning** — Use the appsheet-migration skill for guidance

## Output Files

The parser generates:
- `*-parsed.json` — Canonical versioned JSON with all extracted data

## Error Handling

- If `pdftotext` fails, check the PDF is a valid AppSheet documentation export
- If column count doesn't match header, report the discrepancy with severity
- If the PDF is very large (>50MB), parsing may take 30-60 seconds — this is normal

## Examples

```
/parse-appsheet ~/Downloads/myapp-docs.pdf
/parse-appsheet /tmp/myapp-documentation.pdf
```
