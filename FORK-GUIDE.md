# Fork Guide — Customizing for Your AppSheet App

This guide explains how to fork this repo and specialize it for your specific AppSheet application.

## Why Fork?

The base repo is a **generic** AppSheet documentation parser. It works for any AppSheet app out of the box. But forking lets you:

- Add **domain colors** for your ERD diagrams (group related tables visually)
- **Classify tables** (core vs process vs skip) for smarter migration planning
- Customize the **Claude Code skill** with app-specific migration knowledge
- Pull **upstream improvements** (parser bug fixes, new features) without conflicts

## Step-by-Step

### 1. Fork the Repo

```bash
# On GitHub: click "Fork" on dwertz-at-blenko/appsheet-export-parser
# Then clone your fork:
git clone https://github.com/YOUR-ORG/appsheet-export-parser
cd appsheet-export-parser

# Add upstream remote for pulling updates
git remote add upstream https://github.com/dwertz-at-blenko/appsheet-export-parser
```

### 2. Create Your Config Files

```bash
# Copy the example configs
cp configs/example-domains.yaml configs/myapp-domains.yaml
cp configs/example-app-config.yaml configs/myapp-app-config.yaml
```

Edit `configs/myapp-domains.yaml` — group your tables into color-coded domains:

```yaml
app_name: "My App v2.0"
domains:
  Sales:
    color: "#1565C0"
    fill: "#E3F2FD"
    tables: [Orders, Customers, Products]
  HR:
    color: "#2E7D32"
    fill: "#E8F5E9"
    tables: [Employee, Department, TimeOff]
```

Edit `configs/myapp-app-config.yaml` — classify your tables:

```yaml
table_classification:
  core: [Orders, Customers, Products, Employee]
  process: ["Process for *", "* Output"]
  skip: [Home, Buttons, Dashboard]
migration_target: postgres
```

### 3. (Optional) Customize the Skill

Edit `skill/commands/parse-appsheet.md` to add app-specific knowledge:

```markdown
## App-Specific Notes
- The Orders table has a composite key (OrderID + LineNumber)
- Employee.BadgeNumber should map to VARCHAR(20), not TEXT
- Process tables use a naming convention: "Process for {Action} Process Table"
```

Edit `skill/skills/appsheet-migration/SKILL.md` for migration-specific guidance.

### 4. Install as Claude Code Plugin

```bash
# From your fork's root directory:
claude plugin install ./skill
```

Now `/parse-appsheet` will use your customized configs and skill knowledge.

### 5. Pull Upstream Updates

```bash
git fetch upstream
git merge upstream/main
# Conflicts are rare — configs are new files, not edits to base files
```

## What Goes Where

| Content | Modified in forks? |
|---------|-------------------|
| `src/appsheet_export_parser/` (library code) | **Never** — upstream only |
| `configs/myapp-*.yaml` (your configs) | **Yes** — your customization |
| `skill/` (Claude Code skill) | **Yes** — add app-specific knowledge |
| `tests/fixtures/myapp/` (your test data) | **Yes** — add alongside BERP fixtures |
| Everything else | **No** — upstream maintains |

## Design Principle

Library code (parsing, generation) lives in `src/` and is **never modified in forks**. All app-specific customization happens through **config files** and **skill markdown**. This means forks almost never have merge conflicts on `git pull upstream`.
