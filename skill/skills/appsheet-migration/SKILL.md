---
description: AppSheet migration planning knowledge base — type mappings, patterns, and best practices
---

# AppSheet Migration Planning

Reference knowledge for planning migrations from AppSheet to relational databases (PostgreSQL, MySQL, Supabase).

## When to Use This Skill

This skill provides context when:
- Planning a migration from AppSheet to a relational database
- Interpreting parsed AppSheet documentation output
- Making decisions about schema design, type mappings, or data migration strategy

## AppSheet Type to SQL Mapping

### Core Types

| AppSheet Type | PostgreSQL | MySQL | Notes |
|---------------|-----------|-------|-------|
| Text | TEXT | TEXT | |
| LongText | TEXT | LONGTEXT | |
| Number | NUMERIC | DECIMAL | |
| Decimal | NUMERIC(p,s) | DECIMAL(p,s) | Check MaxValue/MinValue for precision |
| DateTime | TIMESTAMPTZ | DATETIME | |
| Date | DATE | DATE | |
| Time | TIME | TIME | |
| Duration | INTERVAL | TIME | |
| Yes/No | BOOLEAN | TINYINT(1) | |
| Enum | TEXT + CHECK | ENUM(...) | Create CHECK constraint from EnumValues |
| EnumList | TEXT[] | JSON | PostgreSQL arrays vs MySQL JSON |
| Ref | FK constraint | FK constraint | Maps to foreign key |
| Email | TEXT | VARCHAR(255) | Add CHECK for format validation |
| Phone | TEXT | VARCHAR(20) | |
| URL | TEXT | TEXT | |
| Image | TEXT | TEXT | URL to image storage |
| File | TEXT | TEXT | URL to file storage |
| LatLong | POINT | POINT | Or split to lat/lng NUMERIC columns |
| Color | TEXT | VARCHAR(7) | Hex color code |
| ChangeTimestamp | TIMESTAMPTZ DEFAULT NOW() | DATETIME DEFAULT NOW() | Auto-updated |
| ChangeCounter | INTEGER DEFAULT 0 | INT DEFAULT 0 | Auto-incremented on edit |

### Special Types

| AppSheet Type | Migration Strategy |
|---------------|-------------------|
| Show | Skip — UI-only virtual column |
| Virtual columns | Convert app_formula to SQL view or computed column |
| Ref (with IsAPartOf) | Consider composite key or ownership relationship |

## Table Classification

### Core Tables
Real data tables with persistent business data. These need:
- Full schema migration (CREATE TABLE)
- Data migration (INSERT/COPY)
- Index creation
- Foreign key constraints

### Process Tables
AppSheet automation runtime artifacts (e.g., "Process for X", "X Output"). These:
- Document but don't migrate as data tables
- May indicate business logic to implement as services/triggers
- Their column structures reveal workflow requirements

### Skip Tables
UI-only tables (e.g., "Home", "Buttons"). These:
- Exist only for AppSheet navigation/UI
- Have no data to migrate
- Can be completely ignored

## Relationship Patterns

### Ref Columns
AppSheet Ref columns become foreign keys. Check:
- `ReferencedTableName` in TypeQualifier for target table
- `IsAPartOf` flag for ownership/cascade delete
- Column name conventions: `Employee_ID`, `Related Work_Cards`

### Missing References (PDF Limitation)
PDF extraction often loses TypeQualifier JSON at page boundaries. When a Ref column has no target:
1. Check column name for table name hints
2. Look for `_ID` suffix patterns
3. Check if column name matches any table name
4. Use the golden fixture (if available) to verify

### Computed Relationships
Some relationships exist through formulas rather than Ref columns:
- `LOOKUP()` formulas reference other tables
- `REF_ROWS()` creates reverse relationships
- `SELECT()` formulas query across tables

## Migration Phases

### Phase 1: Schema
1. Create database and schema
2. Generate DDL from parsed output
3. Create tables (core tables only)
4. Add indexes on key columns and frequent query columns
5. Add foreign key constraints

### Phase 2: Data
1. Export data from AppSheet (CSV or Google Sheets API)
2. Transform data types (dates, booleans, enums)
3. Load data in dependency order (parent tables first)
4. Validate row counts match source

### Phase 3: Business Logic
1. Convert app_formula to SQL views or computed columns
2. Convert Valid_If to CHECK constraints
3. Convert Actions to API endpoints or triggers
4. Convert Workflow Rules to background jobs
5. Convert Slices to SQL views with row-level filters

### Phase 4: Application Layer
1. Build API endpoints matching AppSheet's data access patterns
2. Implement authentication (AppSheet uses Google Sign-In)
3. Build admin UI (consider Retool, AdminJS, or custom)
4. Implement file/image storage migration

## Risk Assessment Template

When planning a migration, assess:

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data loss during migration | High | Parallel run period, rollback plan |
| Formula complexity | Medium | Categorize formulas by complexity, prioritize simple conversions |
| User adoption | Medium | Training, gradual rollout |
| Integration breakage | High | Map all integrations before migration |
| Performance regression | Medium | Index optimization, query analysis |

## Common Pitfalls

1. **Don't migrate Process tables as data** — they're automation artifacts
2. **Don't ignore EnumList columns** — they need array or JSON storage, not TEXT
3. **Validate Ref targets** — PDF parsing may lose references
4. **Check for circular references** — AppSheet allows them, SQL may not
5. **Map Virtual columns carefully** — some are UI-only (Show type), some have real formulas
6. **Preserve ChangeTimestamp behavior** — add triggers or ORM hooks
7. **Handle image/file URLs** — decide on storage migration strategy early
