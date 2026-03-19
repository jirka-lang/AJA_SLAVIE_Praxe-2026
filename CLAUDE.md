# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Student internship schedule portal ("Praxe") for SK Slavia Praha youth department. Repeats annually (~18 students, ~30 activities, 3-week period in May–June). Token-protected static web app with SQLite database backend.

## Architecture

```
                    LOCAL (not in git)                          GITHUB PAGES (public)
┌──────────────────────────────────────────┐    ┌──────────────────────────────────┐
│ /AJA_AI_SLAVIE/                          │    │ /AJA_AI_SLAVIE/web/ (git root)   │
│   Praxe 2026.xlsx  (source data)         │    │   index.html                     │
│   rozvrh_praxe.py  (scheduler + CLI)     │    │   app.js      (vanilla JS)       │
│   praxe.db         (SQLite database)     │    │   style.css   (responsive)       │
│   STATUS.md                              │    │   data.json   (generated)        │
│                                          │    │   logo-*.jpg                     │
│   web/ ─────────────────────────────────►│    │   CLAUDE.md, STATUS.md           │
└──────────────────────────────────────────┘    └──────────────────────────────────┘
```

**Data flow:** Excel → `migrate` → SQLite DB → `schedule` → DB → `export` → `data.json` → static frontend

The git repository root is `web/`. The parent directory contains the Python script, Excel source, and database — these are NOT in git.

## Key Commands

All commands run from the **parent directory** (`/AJA_AI_SLAVIE/`), not from `web/`.

```bash
# Import Excel data into SQLite (repeatable — clears and reimports)
python3 rozvrh_praxe.py migrate "Praxe 2026.xlsx" --year 2026

# Run scheduling algorithm (reads from DB, writes assignments to DB)
python3 rozvrh_praxe.py schedule --season 2026

# Export data.json for web portal
python3 rozvrh_praxe.py export --season 2026 --output web/data.json

# Show student access URLs
python3 rozvrh_praxe.py tokens --season 2026

# Clone activities for next year (dates set to TBD, students not copied)
python3 rozvrh_praxe.py clone --from 2026 --to 2027

# Data management
python3 rozvrh_praxe.py list-students --season 2026
python3 rozvrh_praxe.py list-activities --season 2026
python3 rozvrh_praxe.py add-student --season 2026 --name "..." --start 2026-05-18 --end 2026-06-05 --school "..."
python3 rozvrh_praxe.py add-activity --season 2026 --name "..." --type "Turnaj" --dates "25.5.2026"

# Legacy mode (bypass DB, process Excel directly — backward compatible)
python3 rozvrh_praxe.py legacy "Praxe 2026.xlsx"
```

### Local frontend development
```bash
cd web && python3 -m http.server 8080
# Open http://localhost:8080/?t=d0a33c9d (any valid token)
```

### Deploy
```bash
cd web && git add data.json && git commit -m "Aktualizace rozvrhu" && git push
```
Live: `https://jirka-lang.github.io/AJA_SLAVIE_Praxe-2026/`

## Backend Architecture (rozvrh_praxe.py)

Single-file Python script (~1950 lines) with these sections:

1. **Data models** — `Activity`, `Student`, `Assignment` dataclasses
2. **Parsing helpers** — `parse_date_field()`, `parse_time_field()`, `parse_capacity()` for Excel cell values
3. **Excel reader** — `read_activities(ws)`, `read_students(ws)` from openpyxl worksheets
4. **Scheduling algorithm** — `schedule(activities, students)` — 5-tier priority system:
   - Tier 1: Fixed date + limited capacity (highest priority)
   - Tier 2: Fixed date + unlimited capacity
   - Tier 3: Multi-day + limited capacity
   - Tier 4: Flexible lectures (1h, placed in lecture week first)
   - Tier 5: Gap-filling with remaining multi-day activities
   - Weekend compensation: 1 day off per weekend worked
5. **Excel writer** — 4 output sheets (Analýza potřeb, Rozvrh-Matice, Rozvrh-Detail, Souhrn)
6. **JSON export** — `export_json()` generates `data.json` for the frontend
7. **Database layer** — SQLite schema, CRUD functions, audit log
8. **CLI commands** — argparse subcommands (migrate, schedule, export, tokens, clone, etc.)

**Dependencies:** `openpyxl` (Excel), `sqlite3` (stdlib). No other external packages.

## Database Schema (praxe.db)

```
season          — year, period, token_salt, is_active
activity        — per season: name, type, organizer, contact (private), capacity, times
activity_date   — M:N: specific dates for each activity
student         — per season: name, school, contacts (private), token
repre_conflict  — dates when repre players are unavailable
assignment      — scheduling results: student × activity × date × time
audit_log       — append-only change tracking
```

Contacts (phone, email) exist ONLY in the database. They are never exported to `data.json` or any public file.

## Frontend Architecture

Vanilla HTML/CSS/JS, no build step, no frameworks.

`app.js` flow: `init()` → fetch `data.json` → validate `?t=TOKEN` → `showDashboard()` or `showGate()`.

**Responsive:** Desktop `<table>`, mobile (<600px) card layout. Both rendered by `renderSchedule()`.

**Activity types** color-coded via CSS class mapping in `activityTypeClass()`: keyword matching on the type string (e.g. "asisten" → `type-asistence`, "turnaj" → `type-turnaj`).

## data.json Contract

```json
{
  "last_updated": "YYYY-MM-DD",
  "period": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" },
  "students": {
    "TOKEN_8CHAR": {
      "name": "...", "school": "...", "school_class": "...", "category": "...",
      "start": "YYYY-MM-DD", "end": "YYYY-MM-DD",
      "schedule": {
        "YYYY-MM-DD": [{ "time": "HH:MM-HH:MM", "activity": "...", "type": "...", "organizer": "..." }]
      },
      "stats": { "total_hours": N, "total_days": N, "activities_count": N }
    }
  }
}
```

No `contact` field in schedule items — removed for security. Frontend handles its absence gracefully.

## Branding

SK Slavia Praha: Red `#CC0000`, Dark `#1A1A1A`, White `#FAFAFA`. Fonts: Oswald (headings), Inter (body). CSS custom properties in `style.css`.

## Language

All UI text is in Czech. CLI output is in Czech. Date formatting uses Czech names (`CZ_MONTHS`, `CZ_DAYS` in `app.js`; `CZ_DAYS` dict in `rozvrh_praxe.py`).

## Security

- `praxe.db` and `pristupy_studentu.xlsx` are in `.gitignore` — never commit
- Student contacts (phone, email) exist only in the SQLite database
- `data.json` contains only: name, school, class, category, schedule, stats
- Token: SHA-256 hash of `{idx}-{name}-{salt}`, 8-char hex, per-season salt
- Git committer email for this repo: `251894153+jirka-lang@users.noreply.github.com`
