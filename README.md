# AppSheet Export Parser

Parse AppSheet documentation exports into structured JSON, ERDs, and migration DDL.

## Installation

```bash
pip install appsheet-export-parser
```

## Quick Start

```bash
# Parse an AppSheet documentation PDF
appsheet-parse parse myapp-docs.pdf -o myapp.json

# Parse from live URL (preferred — better data quality)
appsheet-parse parse "https://appsheet.com/template/appdoc?appId=..." -o myapp.json
```

## Claude Code Skill

The primary interface is the `/parse-appsheet` Claude Code skill:

```
/parse-appsheet ~/Downloads/myapp-docs.pdf
```

See [FORK-GUIDE.md](FORK-GUIDE.md) for customizing the parser for your specific AppSheet app.

## License

MIT
