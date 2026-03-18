#!/usr/bin/env python3
"""Rozvrh praxí mládeže SK Slavia Praha – scheduler & Excel writer."""

import re
import sys
import argparse
import csv
import json
import hashlib
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from pathlib import Path
from typing import Optional
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── Constants ──────────────────────────────────────────────────────────────────

WORK_START = time(8, 0)
WORK_END = time(15, 0)
WORK_HOURS = 7  # 8:00-15:00

CZ_DAYS = {0: "Po", 1: "Út", 2: "St", 3: "Čt", 4: "Pá", 5: "So", 6: "Ne"}

COLORS = {
    "Asistenční činnost": "BDD7EE",
    "Asistenční činnost / výpomoc": "BDD7EE",
    "Turnaj": "F8CBAD",
    "vyučování": "C6EFCE",
    "Absolvování přednášky": "D9E2F3",
    "Absolvování přednášky/ Asistenční činnost / výpomoc": "E2EFDA",
    "Sledování vzorové hodiny": "FCE4D6",
    "volno": "F2F2F2",
    "neaktivní": "D9D9D9",
    "gap": "FF9999",
}

THIN_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"),
)

# ── Data Models ────────────────────────────────────────────────────────────────

@dataclass
class Activity:
    row: int
    name: str
    dates: list  # list[date] or empty if TBD
    time_start: Optional[time]
    time_end: Optional[time]
    duration_hours: float
    activity_type: str
    organizer: str
    capacity: Optional[int]  # None = unlimited
    contact: str
    is_tbd: bool = False
    is_flexible_lecture: bool = False
    is_multiday: bool = False

@dataclass
class Student:
    idx: int
    name: str
    start_date: date
    end_date: date
    school_class: str
    category: str
    school: str
    phone: str
    email: str
    is_repre: bool = False
    repre_unavailable: list = field(default_factory=list)
    notes: str = ""

@dataclass
class Assignment:
    activity_name: str
    activity_type: str
    time_start: time
    time_end: time
    hours: float

# ── Parsing Helpers ────────────────────────────────────────────────────────────

def parse_date_str(s: str, default_year: int = 2026) -> Optional[date]:
    s = s.strip().rstrip(".")
    m = re.match(r"(\d{1,2})\.\s*(\d{1,2})(?:\.\s*(\d{4}))?", s)
    if not m:
        return None
    day, month = int(m.group(1)), int(m.group(2))
    year = int(m.group(3)) if m.group(3) else default_year
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_date_field(raw, default_year: int = 2026):
    if raw is None:
        return [], True
    raw = str(raw).strip()
    if raw == "?" or raw == "":
        return [], True

    # Check for date range: "18.5. - 5.6.2026" or "25.5.-29.5." etc.
    range_match = re.match(
        r"(\d{1,2}\.\s*\d{1,2}\.?\s*\d{0,4})\s*-\s*(\d{1,2}\.\s*\d{1,2}\.?\s*\d{0,4})",
        raw
    )
    if range_match:
        d1 = parse_date_str(range_match.group(1), default_year)
        d2 = parse_date_str(range_match.group(2), default_year)
        if d1 and d2:
            dates = []
            current = d1
            while current <= d2:
                dates.append(current)
                current += timedelta(days=1)
            return dates, False
        return [], True

    # Single date
    d = parse_date_str(raw, default_year)
    if d:
        return [d], False
    return [], True


def parse_time_field(raw):
    if raw is None:
        return None, None, WORK_HOURS
    raw = str(raw).strip()

    # Flexible lecture: "1 hod kdykoliv mezi 8-15:00"
    if "kdykoliv" in raw or "1 hod" in raw.lower():
        return None, None, 1.0  # flexible

    # Standard: "8:00-15:00", "12:30-  14:00", "9:00 - 13:00"
    m = re.match(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", raw)
    if m:
        t1 = time(int(m.group(1)), int(m.group(2)))
        t2 = time(int(m.group(3)), int(m.group(4)))
        h1 = t1.hour + t1.minute / 60.0
        h2 = t2.hour + t2.minute / 60.0
        return t1, t2, h2 - h1
    return None, None, WORK_HOURS


def parse_capacity(raw):
    if raw is None or str(raw).strip() == "":
        return None  # unknown → treat as unlimited
    s = str(raw).strip().lower()
    if "neomez" in s:
        return None
    # "2-3" → take lower bound
    m = re.match(r"(\d+)\s*-\s*(\d+)", s)
    if m:
        return int(m.group(1))
    m = re.match(r"(\d+)", s)
    if m:
        return int(m.group(1))
    return None


# ── Excel Reader ───────────────────────────────────────────────────────────────

def read_activities(ws) -> list:
    activities = []
    for row_idx in range(2, ws.max_row + 1):
        name = ws.cell(row=row_idx, column=1).value
        if not name or str(name).strip() == "":
            continue
        name = str(name).strip()
        # Skip header-like rows
        if name.startswith("Podmínky") or name.startswith("čas plnění") or name.startswith("Kdo bude"):
            continue

        date_raw = ws.cell(row=row_idx, column=2).value
        time_raw = ws.cell(row=row_idx, column=3).value
        atype = str(ws.cell(row=row_idx, column=4).value or "").strip()
        org = str(ws.cell(row=row_idx, column=5).value or "").strip()
        cap_raw = ws.cell(row=row_idx, column=6).value
        contact = str(ws.cell(row=row_idx, column=7).value or "").strip()

        dates, is_tbd = parse_date_field(date_raw)
        t_start, t_end, dur = parse_time_field(time_raw)
        capacity = parse_capacity(cap_raw)

        is_flexible = (dur == 1.0 and t_start is None and "přednášk" in atype.lower())
        is_multiday = len(dates) > 1

        if t_start is None and not is_flexible and not is_tbd:
            t_start = WORK_START
            t_end = WORK_END

        act = Activity(
            row=row_idx, name=name, dates=dates,
            time_start=t_start, time_end=t_end, duration_hours=dur,
            activity_type=atype, organizer=org, capacity=capacity,
            contact=contact, is_tbd=is_tbd,
            is_flexible_lecture=is_flexible, is_multiday=is_multiday,
        )
        activities.append(act)
    return activities


def read_students(ws) -> list:
    students = []
    for row_idx in range(5, ws.max_row + 1):
        idx_val = ws.cell(row=row_idx, column=1).value
        name_val = ws.cell(row=row_idx, column=2).value
        if not name_val or str(name_val).strip() == "":
            continue

        date_raw = ws.cell(row=row_idx, column=3).value
        dates, _ = parse_date_field(date_raw)
        if len(dates) < 2:
            continue

        start_d = min(dates)
        end_d = max(dates)
        # Jarov: if start is Sunday 25.5., shift to Monday 26.5.
        if start_d.weekday() == 6:
            start_d = start_d + timedelta(days=1)

        school_class = str(ws.cell(row=row_idx, column=5).value or "").strip()
        category = str(ws.cell(row=row_idx, column=6).value or "").strip()
        school = str(ws.cell(row=row_idx, column=7).value or "").strip()
        phone = str(ws.cell(row=row_idx, column=8).value or "").strip()
        email = str(ws.cell(row=row_idx, column=9).value or "").strip()
        notes = str(ws.cell(row=row_idx, column=10).value or "").strip()
        is_repre = "repre" in notes.lower() or "repre" in category.lower()

        students.append(Student(
            idx=int(idx_val) if idx_val else len(students) + 1,
            name=str(name_val).strip(),
            start_date=start_d, end_date=end_d,
            school_class=school_class, category=category, school=school,
            phone=phone, email=email, is_repre=is_repre, notes=notes,
        ))
    return students


def load_repre_conflicts(path: str, students: list):
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 3:
                    continue
                cat = row[0].strip()
                dates, _ = parse_date_field(f"{row[1].strip()} - {row[2].strip()}")
                for s in students:
                    if s.category.upper() == cat.upper():
                        s.repre_unavailable.extend(dates)
    except FileNotFoundError:
        pass


# ── Calendar & Scheduling ─────────────────────────────────────────────────────

def get_working_days(start: date, end: date) -> list:
    """All days (incl weekends for weekend activities) from start to end."""
    days = []
    d = start
    while d <= end:
        days.append(d)
        d += timedelta(days=1)
    return days


def get_weekdays(start: date, end: date) -> list:
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def student_available_days(s: Student) -> list:
    """Weekdays the student is available (excl repre conflicts)."""
    days = get_weekdays(s.start_date, s.end_date)
    return [d for d in days if d not in s.repre_unavailable]


def schedule(activities: list, students: list):
    """Main scheduling algorithm. Returns schedule dict: {student_idx: {date: [Assignment]}}"""

    # Initialize schedule: student_idx → {date → [Assignment]}
    sched = {}
    for s in students:
        sched[s.idx] = {}
        for d in student_available_days(s):
            sched[s.idx][d] = []

    # Track capacity usage: activity_row → {date → count}
    cap_usage = {}
    for a in activities:
        cap_usage[a.row] = {}

    # Weekend assignments tracker for compensatory day off
    weekend_work = {}  # student_idx → set of weekend dates worked

    def hours_filled(student_idx, d):
        return sum(a.hours for a in sched[student_idx].get(d, []))

    def hours_remaining(student_idx, d):
        return WORK_HOURS - hours_filled(student_idx, d)

    def can_assign(student_idx, act, d):
        if d not in sched[student_idx]:
            return False
        remaining = hours_remaining(student_idx, d)
        if remaining < act.duration_hours - 0.01:
            return False
        # Check capacity
        if act.capacity is not None:
            used = cap_usage[act.row].get(d, 0)
            if used >= act.capacity:
                return False
        return True

    def do_assign(student_idx, act, d, t_start=None, t_end=None):
        if t_start is None:
            # Find next available slot
            filled = hours_filled(student_idx, d)
            h = 8 + filled
            t_start = time(int(h), int((h % 1) * 60))
            h2 = h + act.duration_hours
            t_end = time(int(h2), int((h2 % 1) * 60))

        asgn = Assignment(
            activity_name=act.name, activity_type=act.activity_type,
            time_start=t_start, time_end=t_end, hours=act.duration_hours,
        )
        sched[student_idx][d].append(asgn)
        cap_usage[act.row][d] = cap_usage[act.row].get(d, 0) + 1

        # Track weekend work
        if d.weekday() >= 5:
            if student_idx not in weekend_work:
                weekend_work[student_idx] = set()
            weekend_work[student_idx].add(d)

    def score_student(s, act, d):
        sc = 0
        sc += hours_remaining(s.idx, d) * 0.5  # prefer students with more free time
        # Variety: how many unique types does student already have?
        types_done = set()
        for dd, asgs in sched[s.idx].items():
            for a in asgs:
                types_done.add(a.activity_type)
        if act.activity_type not in types_done:
            sc += 2
        # Category match for gender-specific events
        if "girl" in act.name.lower() or "wu" in act.name.lower():
            if "WU" in s.category.upper():
                sc += 1
        # Repre penalty
        if d in s.repre_unavailable:
            sc -= 10
        return sc

    # ── Tier 1: Fixed date + limited capacity ──
    tier1 = [a for a in activities if not a.is_tbd and not a.is_flexible_lecture
             and a.capacity is not None and not a.is_multiday]
    tier1.sort(key=lambda a: (min(a.dates) if a.dates else date.max, a.capacity or 999))

    for act in tier1:
        for d in act.dates:
            candidates = [s for s in students if can_assign(s.idx, act, d)]
            candidates.sort(key=lambda s: score_student(s, act, d), reverse=True)
            limit = act.capacity or len(candidates)
            for s in candidates[:limit]:
                t_s = act.time_start or WORK_START
                t_e = act.time_end or WORK_END
                do_assign(s.idx, act, d, t_s, t_e)

    # ── Tier 2: Fixed date + unlimited capacity ──
    tier2 = [a for a in activities if not a.is_tbd and not a.is_flexible_lecture
             and a.capacity is None and not a.is_multiday]

    for act in tier2:
        for d in act.dates:
            for s in students:
                if can_assign(s.idx, act, d) and hours_remaining(s.idx, d) >= act.duration_hours:
                    t_s = act.time_start or WORK_START
                    t_e = act.time_end or WORK_END
                    do_assign(s.idx, act, d, t_s, t_e)

    # ── Tier 3: Multi-day + limited capacity (Fan shop, observations) ──
    tier3 = [a for a in activities if not a.is_tbd and not a.is_flexible_lecture
             and a.is_multiday and a.capacity is not None]

    for act in tier3:
        weekday_dates = [d for d in act.dates if d.weekday() < 5]
        for d in weekday_dates:
            if act.capacity is not None and cap_usage[act.row].get(d, 0) >= act.capacity:
                continue
            candidates = [s for s in students if can_assign(s.idx, act, d)]
            candidates.sort(key=lambda s: score_student(s, act, d), reverse=True)
            limit = act.capacity or len(candidates)
            needed = limit - cap_usage[act.row].get(d, 0)
            for s in candidates[:needed]:
                t_s = act.time_start or WORK_START
                t_e = act.time_end or WORK_END
                do_assign(s.idx, act, d, t_s, t_e)

    # ── Tier 4: Flexible lectures (9 lectures, 1h each, week 25.5.-29.5.) ──
    lectures = [a for a in activities if a.is_flexible_lecture]
    lecture_week = get_weekdays(date(2026, 5, 25), date(2026, 5, 29))

    for s in students:
        available_lec_days = [d for d in lecture_week if d in sched[s.idx]]
        remaining_lectures = list(lectures)

        for d in available_lec_days:
            while remaining_lectures and hours_remaining(s.idx, d) >= 1.0:
                lec = remaining_lectures.pop(0)
                do_assign(s.idx, lec, d)
            if not remaining_lectures:
                break

        # If student wasn't available during lecture week, try other days
        if remaining_lectures:
            all_days = sorted(sched[s.idx].keys())
            for d in all_days:
                while remaining_lectures and hours_remaining(s.idx, d) >= 1.0:
                    lec = remaining_lectures.pop(0)
                    do_assign(s.idx, lec, d)
                if not remaining_lectures:
                    break

    # ── Tier 5: Fill remaining gaps with any available multi-day activities ──
    # Priority: unlimited first, then limited (Fan shop etc.)
    filler_unlimited = [a for a in activities if not a.is_tbd and not a.is_flexible_lecture
                        and a.is_multiday and a.capacity is None]
    filler_limited = [a for a in activities if not a.is_tbd and not a.is_flexible_lecture
                      and a.is_multiday and a.capacity is not None]

    def fill_gap(s_idx, d, filler_list, check_capacity=False):
        remaining = hours_remaining(s_idx, d)
        for act in filler_list:
            if remaining < 0.5:
                break
            if d not in act.dates:
                continue
            if check_capacity and act.capacity is not None:
                if cap_usage[act.row].get(d, 0) >= act.capacity:
                    continue
            fill_hours = min(remaining, act.duration_hours)
            filled_h = hours_filled(s_idx, d)
            h_start = 8 + filled_h
            h_end = h_start + fill_hours
            t_s = time(int(h_start), int((h_start % 1) * 60))
            t_e = time(int(h_end), int((h_end % 1) * 60))
            asgn = Assignment(
                activity_name=act.name, activity_type=act.activity_type,
                time_start=t_s, time_end=t_e, hours=fill_hours,
            )
            sched[s_idx][d].append(asgn)
            cap_usage[act.row][d] = cap_usage[act.row].get(d, 0) + 1
            remaining = hours_remaining(s_idx, d)

    for s in students:
        for d in sorted(sched[s.idx].keys()):
            if hours_remaining(s.idx, d) < 0.5:
                continue
            # First try unlimited fillers (stáž, úklid okolí, etc.)
            fill_gap(s.idx, d, filler_unlimited, check_capacity=False)
            # Then try limited fillers (Fan shop)
            if hours_remaining(s.idx, d) >= 0.5:
                fill_gap(s.idx, d, filler_limited, check_capacity=True)

    # ── Handle weekend compensatory days ──
    for s_idx, weekend_dates in weekend_work.items():
        student = next(s for s in students if s.idx == s_idx)
        weekdays = sorted([d for d in sched[s_idx] if d.weekday() < 5])
        # Remove one weekday per weekend worked (pick the one with least assignments)
        for _ in weekend_dates:
            if weekdays:
                # Pick day with fewest hours already assigned
                best = min(weekdays, key=lambda d: hours_filled(s_idx, d))
                sched[s_idx][best] = [Assignment(
                    activity_name="VOLNO (kompenzace víkendu)",
                    activity_type="volno", time_start=WORK_START,
                    time_end=WORK_END, hours=WORK_HOURS,
                )]
                weekdays.remove(best)

    return sched, cap_usage, weekend_work


# ── TBD Suggestions ───────────────────────────────────────────────────────────

def suggest_tbd_dates(activities, students, sched):
    tbd_acts = [a for a in activities if a.is_tbd]
    suggestions = []
    all_period = get_weekdays(date(2026, 5, 18), date(2026, 6, 5))

    for act in tbd_acts:
        best_date = None
        best_score = -1
        for d in all_period:
            available_students = sum(
                1 for s in students
                if d in sched[s.idx] and
                WORK_HOURS - sum(a.hours for a in sched[s.idx][d]) >= act.duration_hours
            )
            if available_students > best_score:
                best_score = available_students
                best_date = d
        suggestions.append((act, best_date, best_score))
    return suggestions


# ── Excel Writer ───────────────────────────────────────────────────────────────

def format_date_header(d: date) -> str:
    return f"{CZ_DAYS[d.weekday()]} {d.day}.{d.month}."


def write_matrix_sheet(wb, students, sched):
    if "Rozvrh - Matice" in wb.sheetnames:
        del wb["Rozvrh - Matice"]
    ws = wb.create_sheet("Rozvrh - Matice")

    all_dates = sorted(set(d for s in students for d in sched[s.idx]))

    # Headers
    ws.cell(row=1, column=1, value="Student")
    ws.cell(row=1, column=1).font = Font(bold=True, size=10)
    ws.cell(row=1, column=1).alignment = Alignment(horizontal="center")
    ws.column_dimensions["A"].width = 22

    for ci, d in enumerate(all_dates, start=2):
        cell = ws.cell(row=1, column=ci, value=format_date_header(d))
        cell.font = Font(bold=True, size=9)
        cell.alignment = Alignment(horizontal="center", text_rotation=0)
        cell.border = THIN_BORDER
        if d.weekday() >= 5:
            cell.fill = PatternFill("solid", fgColor="FFF2CC")
        ws.column_dimensions[get_column_letter(ci)].width = 20

    # Data rows
    for ri, s in enumerate(students, start=2):
        ws.cell(row=ri, column=1, value=s.name)
        ws.cell(row=ri, column=1).font = Font(bold=True, size=9)
        ws.cell(row=ri, column=1).border = THIN_BORDER

        for ci, d in enumerate(all_dates, start=2):
            cell = ws.cell(row=ri, column=ci)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.font = Font(size=8)

            if d not in sched[s.idx]:
                cell.fill = PatternFill("solid", fgColor=COLORS["neaktivní"])
                cell.value = "—"
                continue

            assignments = sched[s.idx][d]
            if not assignments:
                cell.fill = PatternFill("solid", fgColor=COLORS["gap"])
                cell.value = "NEVYPLNĚNO"
                continue

            lines = []
            main_type = assignments[0].activity_type
            for a in assignments:
                t1 = a.time_start.strftime("%H:%M") if a.time_start else "?"
                t2 = a.time_end.strftime("%H:%M") if a.time_end else "?"
                lines.append(f"{t1}-{t2} {a.activity_name}")
            cell.value = "\n".join(lines)

            color = COLORS.get(main_type, "FFFFFF")
            cell.fill = PatternFill("solid", fgColor=color)

            total_h = sum(a.hours for a in assignments)
            if total_h < WORK_HOURS - 0.5:
                cell.fill = PatternFill("solid", fgColor=COLORS["gap"])

    ws.freeze_panes = "B2"
    ws.sheet_properties.pageSetUpPr = None


def write_detail_sheet(wb, students, sched):
    if "Rozvrh - Detail" in wb.sheetnames:
        del wb["Rozvrh - Detail"]
    ws = wb.create_sheet("Rozvrh - Detail")

    all_dates = sorted(set(d for s in students for d in sched[s.idx]))
    hours_slots = list(range(8, 15))  # 8-9, 9-10, ..., 14-15

    current_row = 1
    for d in all_dates:
        # Day header
        cell = ws.cell(row=current_row, column=1, value=format_date_header(d))
        cell.font = Font(bold=True, size=11)
        cell.fill = PatternFill("solid", fgColor="4472C4")
        cell.font = Font(bold=True, size=11, color="FFFFFF")
        for ci in range(1, len(hours_slots) + 2):
            ws.cell(row=current_row, column=ci).fill = PatternFill("solid", fgColor="4472C4")
        current_row += 1

        # Time headers
        ws.cell(row=current_row, column=1, value="Student")
        ws.cell(row=current_row, column=1).font = Font(bold=True, size=9)
        for hi, h in enumerate(hours_slots, start=2):
            cell = ws.cell(row=current_row, column=hi, value=f"{h}:00-{h+1}:00")
            cell.font = Font(bold=True, size=8)
            cell.alignment = Alignment(horizontal="center")
            cell.border = THIN_BORDER
        current_row += 1

        # Student rows for this day
        for s in students:
            if d not in sched[s.idx]:
                continue
            ws.cell(row=current_row, column=1, value=s.name)
            ws.cell(row=current_row, column=1).font = Font(size=8)
            ws.cell(row=current_row, column=1).border = THIN_BORDER

            assignments = sched[s.idx][d]
            for hi, h in enumerate(hours_slots, start=2):
                cell = ws.cell(row=current_row, column=hi)
                cell.border = THIN_BORDER
                cell.font = Font(size=7)
                cell.alignment = Alignment(horizontal="center", wrap_text=True)

                slot_time = time(h, 0)
                slot_end = time(h + 1, 0)
                found = None
                for a in assignments:
                    a_start_h = a.time_start.hour + a.time_start.minute / 60 if a.time_start else 8
                    a_end_h = a.time_end.hour + a.time_end.minute / 60 if a.time_end else 15
                    if a_start_h <= h < a_end_h:
                        found = a
                        break
                if found:
                    cell.value = found.activity_name[:25]
                    color = COLORS.get(found.activity_type, "FFFFFF")
                    cell.fill = PatternFill("solid", fgColor=color)
                else:
                    cell.value = ""
            current_row += 1

        current_row += 1  # blank row between days

    ws.column_dimensions["A"].width = 22
    for ci in range(2, len(hours_slots) + 2):
        ws.column_dimensions[get_column_letter(ci)].width = 18


def write_summary_sheet(wb, students, activities, sched, cap_usage, suggestions):
    if "Souhrn" in wb.sheetnames:
        del wb["Souhrn"]
    ws = wb.create_sheet("Souhrn")

    header_font = Font(bold=True, size=11)
    header_fill = PatternFill("solid", fgColor="4472C4")
    header_font_w = Font(bold=True, size=11, color="FFFFFF")

    # ── Section 1: Student Statistics ──
    row = 1
    ws.cell(row=row, column=1, value="STATISTIKY STUDENTŮ")
    ws.cell(row=row, column=1).font = header_font_w
    ws.cell(row=row, column=1).fill = header_fill
    for c in range(1, 7):
        ws.cell(row=row, column=c).fill = header_fill
    row += 1

    headers = ["Student", "Škola", "Kategorie", "Celk. hodin", "Nevyplněno (h)", "Počet činností"]
    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=row, column=ci, value=h)
        cell.font = Font(bold=True, size=9)
        cell.border = THIN_BORDER
    row += 1

    for s in students:
        total_h = 0
        total_days = 0
        activity_names = set()
        for d, asgs in sched[s.idx].items():
            total_days += 1
            for a in asgs:
                total_h += a.hours
                activity_names.add(a.activity_name)
        gap_h = max(0, total_days * WORK_HOURS - total_h)

        ws.cell(row=row, column=1, value=s.name).border = THIN_BORDER
        ws.cell(row=row, column=2, value=s.school).border = THIN_BORDER
        ws.cell(row=row, column=3, value=s.category).border = THIN_BORDER
        ws.cell(row=row, column=4, value=round(total_h, 1)).border = THIN_BORDER
        gap_cell = ws.cell(row=row, column=5, value=round(gap_h, 1))
        gap_cell.border = THIN_BORDER
        if gap_h > 0:
            gap_cell.fill = PatternFill("solid", fgColor=COLORS["gap"])
        ws.cell(row=row, column=6, value=len(activity_names)).border = THIN_BORDER
        row += 1

    row += 2

    # ── Section 2: Activity Capacity ──
    ws.cell(row=row, column=1, value="KAPACITY ČINNOSTÍ")
    ws.cell(row=row, column=1).font = header_font_w
    ws.cell(row=row, column=1).fill = header_fill
    for c in range(1, 5):
        ws.cell(row=row, column=c).fill = header_fill
    row += 1

    act_headers = ["Činnost", "Kapacita", "Max přiřazeno/den", "Stav"]
    for ci, h in enumerate(act_headers, 1):
        ws.cell(row=row, column=ci, value=h).font = Font(bold=True, size=9)
        ws.cell(row=row, column=ci).border = THIN_BORDER
    row += 1

    for act in activities:
        if act.is_tbd:
            continue
        max_used = max(cap_usage[act.row].values()) if cap_usage[act.row] else 0
        cap_str = str(act.capacity) if act.capacity else "neomezená"
        status = "OK"
        if act.capacity and max_used > act.capacity:
            status = "PŘEKROČENO!"
        elif act.capacity and max_used == act.capacity:
            status = "Plná"

        ws.cell(row=row, column=1, value=act.name).border = THIN_BORDER
        ws.cell(row=row, column=2, value=cap_str).border = THIN_BORDER
        ws.cell(row=row, column=3, value=max_used).border = THIN_BORDER
        st_cell = ws.cell(row=row, column=4, value=status)
        st_cell.border = THIN_BORDER
        if status == "PŘEKROČENO!":
            st_cell.fill = PatternFill("solid", fgColor="FF0000")
            st_cell.font = Font(color="FFFFFF", bold=True)
        row += 1

    row += 2

    # ── Section 3: TBD Suggestions ──
    ws.cell(row=row, column=1, value="ČINNOSTI S NEURČENÝM TERMÍNEM – DOPORUČENÍ")
    ws.cell(row=row, column=1).font = header_font_w
    ws.cell(row=row, column=1).fill = header_fill
    for c in range(1, 4):
        ws.cell(row=row, column=c).fill = header_fill
    row += 1

    for act, best_date, score in suggestions:
        ws.cell(row=row, column=1, value=act.name).border = THIN_BORDER
        if best_date:
            ws.cell(row=row, column=2, value=f"Doporučený termín: {format_date_header(best_date)}").border = THIN_BORDER
            ws.cell(row=row, column=3, value=f"{score} studentů dostupných").border = THIN_BORDER
        else:
            ws.cell(row=row, column=2, value="Nelze určit").border = THIN_BORDER
        row += 1

    row += 2

    # ── Section 4: Warnings ──
    ws.cell(row=row, column=1, value="VAROVÁNÍ")
    ws.cell(row=row, column=1).font = header_font_w
    ws.cell(row=row, column=1).fill = header_fill
    for c in range(1, 4):
        ws.cell(row=row, column=c).fill = header_fill
    row += 1

    warnings = []
    for s in students:
        for d, asgs in sched[s.idx].items():
            total_h = sum(a.hours for a in asgs)
            if total_h < WORK_HOURS - 0.5 and not any(a.activity_type == "volno" for a in asgs):
                warnings.append(f"{s.name}: {format_date_header(d)} – pouze {total_h:.1f}h z {WORK_HOURS}h vyplněno")

    if s.category == "?":
        warnings.append(f"{s.name}: neznámá kategorie – nelze vyhodnotit repre kolize")

    repre_students = [s for s in students if s.is_repre]
    if repre_students:
        names = ", ".join(s.name for s in repre_students)
        warnings.append(f"Reprezentanti ({names}): termíny výjezdů zatím neupřesněny")

    if not warnings:
        ws.cell(row=row, column=1, value="Žádná varování")
    for w in warnings:
        ws.cell(row=row, column=1, value=w).font = Font(size=9, color="CC0000")
        row += 1

    # Column widths
    ws.column_dimensions["A"].width = 45
    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 25
    ws.column_dimensions["D"].width = 15
    ws.column_dimensions["E"].width = 15
    ws.column_dimensions["F"].width = 15


def write_analysis_sheet(wb, students, activities, sched):
    """List 'Analýza potřeb' – podklad pro jednání s organizátory o termínech."""
    if "Analýza potřeb" in wb.sheetnames:
        del wb["Analýza potřeb"]
    ws = wb.create_sheet("Analýza potřeb", 0)  # First sheet for visibility

    header_fill = PatternFill("solid", fgColor="4472C4")
    header_font = Font(bold=True, size=11, color="FFFFFF")
    section_fill = PatternFill("solid", fgColor="D6E4F0")
    section_font = Font(bold=True, size=10)

    all_dates = get_weekdays(date(2026, 5, 18), date(2026, 6, 5))

    row = 1
    # ── Section 1: Availability heatmap – how many students available per day ──
    ws.cell(row=row, column=1, value="DOSTUPNOST STUDENTŮ PO DNECH")
    ws.cell(row=row, column=1).font = header_font
    for c in range(1, len(all_dates) + 2):
        ws.cell(row=row, column=c).fill = header_fill
    row += 1

    # Sub-header
    ws.cell(row=row, column=1, value="Metrika").font = Font(bold=True, size=9)
    ws.cell(row=row, column=1).border = THIN_BORDER
    for ci, d in enumerate(all_dates, start=2):
        cell = ws.cell(row=row, column=ci, value=format_date_header(d))
        cell.font = Font(bold=True, size=8)
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER
        ws.column_dimensions[get_column_letter(ci)].width = 12
    row += 1

    # Row: total students on practice that day
    ws.cell(row=row, column=1, value="Studentů na praxi")
    ws.cell(row=row, column=1).font = Font(bold=True, size=9)
    ws.cell(row=row, column=1).border = THIN_BORDER
    for ci, d in enumerate(all_dates, start=2):
        count = sum(1 for s in students if s.start_date <= d <= s.end_date and d.weekday() < 5)
        cell = ws.cell(row=row, column=ci, value=count)
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER
        if count >= 15:
            cell.fill = PatternFill("solid", fgColor="C6EFCE")
        elif count >= 5:
            cell.fill = PatternFill("solid", fgColor="FFEB9C")
        else:
            cell.fill = PatternFill("solid", fgColor="FFC7CE")
    row += 1

    # Row: unfilled student-hours that day (AFTER scheduling)
    ws.cell(row=row, column=1, value="Nevyplněné hodiny (celkem)")
    ws.cell(row=row, column=1).font = Font(bold=True, size=9)
    ws.cell(row=row, column=1).border = THIN_BORDER
    for ci, d in enumerate(all_dates, start=2):
        gap_h = 0
        for s in students:
            if d in sched[s.idx]:
                filled = sum(a.hours for a in sched[s.idx][d])
                gap_h += max(0, WORK_HOURS - filled)
        cell = ws.cell(row=row, column=ci, value=round(gap_h, 1))
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER
        if gap_h > 20:
            cell.fill = PatternFill("solid", fgColor="FF0000")
            cell.font = Font(color="FFFFFF", bold=True)
        elif gap_h > 5:
            cell.fill = PatternFill("solid", fgColor="FFC7CE")
        elif gap_h > 0:
            cell.fill = PatternFill("solid", fgColor="FFEB9C")
        else:
            cell.fill = PatternFill("solid", fgColor="C6EFCE")
    row += 1

    # Row: confirmed activities that day
    ws.cell(row=row, column=1, value="Potvrzených činností")
    ws.cell(row=row, column=1).font = Font(bold=True, size=9)
    ws.cell(row=row, column=1).border = THIN_BORDER
    for ci, d in enumerate(all_dates, start=2):
        count = sum(1 for a in activities if not a.is_tbd and d in a.dates)
        cell = ws.cell(row=row, column=ci, value=count)
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER
    row += 2

    # ── Section 2: Per-school breakdown ──
    ws.cell(row=row, column=1, value="DOSTUPNOST PO ŠKOLÁCH")
    ws.cell(row=row, column=1).font = header_font
    for c in range(1, len(all_dates) + 2):
        ws.cell(row=row, column=c).fill = header_fill
    row += 1

    schools = {}
    for s in students:
        schools.setdefault(s.school, []).append(s)

    for school_name, school_students in schools.items():
        ws.cell(row=row, column=1, value=school_name)
        ws.cell(row=row, column=1).font = section_font
        ws.cell(row=row, column=1).fill = section_fill
        ws.cell(row=row, column=1).border = THIN_BORDER
        for ci, d in enumerate(all_dates, start=2):
            count = sum(1 for s in school_students if s.start_date <= d <= s.end_date and d.weekday() < 5)
            cell = ws.cell(row=row, column=ci, value=count if count > 0 else "—")
            cell.alignment = Alignment(horizontal="center")
            cell.border = THIN_BORDER
            cell.fill = section_fill if count > 0 else PatternFill("solid", fgColor="D9D9D9")
        row += 1

        for s in school_students:
            ws.cell(row=row, column=1, value=f"  {s.name} ({s.category})")
            ws.cell(row=row, column=1).font = Font(size=8)
            ws.cell(row=row, column=1).border = THIN_BORDER
            for ci, d in enumerate(all_dates, start=2):
                cell = ws.cell(row=row, column=ci)
                cell.border = THIN_BORDER
                cell.alignment = Alignment(horizontal="center")
                cell.font = Font(size=8)
                if d not in sched[s.idx]:
                    cell.value = "—"
                    cell.fill = PatternFill("solid", fgColor="D9D9D9")
                else:
                    filled = sum(a.hours for a in sched[s.idx][d])
                    gap = WORK_HOURS - filled
                    if gap < 0.5:
                        cell.value = f"{filled:.0f}h"
                        cell.fill = PatternFill("solid", fgColor="C6EFCE")
                    else:
                        cell.value = f"{filled:.0f}/{WORK_HOURS}h"
                        cell.fill = PatternFill("solid", fgColor="FFC7CE")
            row += 1
        row += 1

    row += 1

    # ── Section 3: TBD Activities – Recommended dates ──
    ws.cell(row=row, column=1, value="ČINNOSTI BEZ POTVRZENÉHO TERMÍNU – DOPORUČENÍ PRO JEDNÁNÍ")
    ws.cell(row=row, column=1).font = header_font
    for c in range(1, 6):
        ws.cell(row=row, column=c).fill = header_fill
    row += 1

    tbd_headers = ["Činnost", "Typ", "Kapacita", "Doporučený termín", "Dostupných studentů"]
    for ci, h in enumerate(tbd_headers, 1):
        ws.cell(row=row, column=ci, value=h).font = Font(bold=True, size=9)
        ws.cell(row=row, column=ci).border = THIN_BORDER
    row += 1

    tbd_acts = [a for a in activities if a.is_tbd]
    for act in tbd_acts:
        # Find best 3 dates based on students with gaps
        day_scores = []
        for d in all_dates:
            available = 0
            for s in students:
                if s.start_date <= d <= s.end_date and d.weekday() < 5:
                    filled = sum(ag.hours for ag in sched[s.idx].get(d, []))
                    if WORK_HOURS - filled >= min(act.duration_hours, 3):
                        available += 1
            day_scores.append((d, available))
        day_scores.sort(key=lambda x: x[1], reverse=True)
        top3 = day_scores[:3]

        ws.cell(row=row, column=1, value=act.name).border = THIN_BORDER
        ws.cell(row=row, column=2, value=act.activity_type).border = THIN_BORDER
        ws.cell(row=row, column=3, value=str(act.capacity) if act.capacity else "neomez.").border = THIN_BORDER
        recs = ", ".join(f"{format_date_header(d)} ({sc} st. volných)" for d, sc in top3 if sc > 0)
        if not recs:
            # All students fully booked – show days with most students present
            presence = []
            for d in all_dates:
                present = sum(1 for s in students if s.start_date <= d <= s.end_date and d.weekday() < 5)
                presence.append((d, present))
            presence.sort(key=lambda x: x[1], reverse=True)
            recs = ", ".join(f"{format_date_header(d)} ({p} st. přítomno)" for d, p in presence[:3])
        ws.cell(row=row, column=4, value=recs).border = THIN_BORDER
        ws.cell(row=row, column=5, value=f"Top: {top3[0][1]} s mezerami" if top3 and top3[0][1] > 0 else "Všichni plní – nutné přeplánovat").border = THIN_BORDER
        row += 1

    row += 2

    # ── Section 4: Days with biggest gaps – where new activities are needed ──
    ws.cell(row=row, column=1, value="DNY S NEJVĚTŠÍMI MEZERAMI – KDE DOMLUVIT DALŠÍ ČINNOSTI")
    ws.cell(row=row, column=1).font = header_font
    for c in range(1, 5):
        ws.cell(row=row, column=c).fill = header_fill
    row += 1

    gap_headers = ["Den", "Studentů na praxi", "Nevyplněné hodiny", "Doporučení"]
    for ci, h in enumerate(gap_headers, 1):
        ws.cell(row=row, column=ci, value=h).font = Font(bold=True, size=9)
        ws.cell(row=row, column=ci).border = THIN_BORDER
    row += 1

    day_gaps = []
    for d in all_dates:
        total_students = sum(1 for s in students if d in sched[s.idx])
        gap_h = sum(
            max(0, WORK_HOURS - sum(a.hours for a in sched[s.idx].get(d, [])))
            for s in students if d in sched[s.idx]
        )
        if gap_h > 0.5:
            day_gaps.append((d, total_students, gap_h))

    day_gaps.sort(key=lambda x: x[2], reverse=True)
    for d, total_st, gap_h in day_gaps:
        ws.cell(row=row, column=1, value=format_date_header(d)).border = THIN_BORDER
        ws.cell(row=row, column=2, value=total_st).border = THIN_BORDER
        gap_cell = ws.cell(row=row, column=3, value=f"{gap_h:.1f}h")
        gap_cell.border = THIN_BORDER
        gap_cell.fill = PatternFill("solid", fgColor="FFC7CE")

        # Recommendation
        if gap_h > 30:
            rec = f"KRITICKÉ: chybí celodenní aktivita pro {int(gap_h/7)}+ studentů"
        elif gap_h > 10:
            rec = f"Doporučení: domluvit aktivitu na {int(gap_h)}h celkem"
        else:
            rec = "Malé mezery – doplnitelné přednáškami/stáží"
        ws.cell(row=row, column=4, value=rec).border = THIN_BORDER
        row += 1

    row += 2

    # ── Section 5: Repre conflict zones ──
    ws.cell(row=row, column=1, value="REPREZENTAČNÍ KATEGORIE – POTENCIÁLNÍ KOLIZE")
    ws.cell(row=row, column=1).font = header_font
    for c in range(1, 4):
        ws.cell(row=row, column=c).fill = header_fill
    row += 1

    categories = {}
    for s in students:
        if s.category and s.category != "?":
            categories.setdefault(s.category, []).append(s.name)

    for cat, names in sorted(categories.items()):
        ws.cell(row=row, column=1, value=cat).border = THIN_BORDER
        ws.cell(row=row, column=1).font = Font(bold=True, size=9)
        ws.cell(row=row, column=2, value=", ".join(names)).border = THIN_BORDER
        status = "UPŘESNIT termíny výjezdů"
        repre_in_cat = [s for s in students if s.category == cat and s.is_repre]
        if repre_in_cat:
            status = "POZOR: " + ", ".join(s.name for s in repre_in_cat) + " – repre potvrzeno"
        ws.cell(row=row, column=3, value=status).border = THIN_BORDER
        ws.cell(row=row, column=3).font = Font(size=9, color="CC0000" if "POZOR" in status else "000000")
        row += 1

    # Column widths
    ws.column_dimensions["A"].width = 45
    ws.column_dimensions["B"].width = 15
    ws.column_dimensions["C"].width = 15
    ws.column_dimensions["D"].width = 50
    ws.column_dimensions["E"].width = 20


# ── JSON Export for Web Portal ────────────────────────────────────────────────

TOKEN_SALT = "SK-Slavia-Praha-Praxe-2026"


def generate_token(student: Student) -> str:
    """Generate a short unique token for a student (8 chars of SHA-256)."""
    raw = f"{student.idx}-{student.name}-{TOKEN_SALT}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


def export_json(students: list, activities: list, sched: dict, output_dir: str):
    """Export schedule data as JSON for the web portal."""

    period_start = min(s.start_date for s in students)
    period_end = max(s.end_date for s in students)

    # Build activity lookup for contact/organizer info
    act_lookup = {}
    for a in activities:
        act_lookup[a.name] = {
            "organizer": a.organizer,
            "contact": a.contact,
            "type": a.activity_type,
        }

    data = {
        "last_updated": date.today().isoformat(),
        "period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "students": {},
    }

    token_map = {}  # student_idx → token (for Excel column)

    for s in students:
        token = generate_token(s)
        token_map[s.idx] = token

        student_schedule = {}
        for d in sorted(sched[s.idx].keys()):
            day_items = []
            for asgn in sched[s.idx][d]:
                info = act_lookup.get(asgn.activity_name, {})
                day_items.append({
                    "time": f"{asgn.time_start.strftime('%H:%M')}-{asgn.time_end.strftime('%H:%M')}",
                    "activity": asgn.activity_name,
                    "type": asgn.activity_type,
                    "organizer": info.get("organizer", ""),
                    "contact": info.get("contact", ""),
                })
            if day_items:
                student_schedule[d.isoformat()] = day_items

        total_hours = sum(a.hours for d_asgs in sched[s.idx].values() for a in d_asgs)
        total_days = len([d for d in sched[s.idx] if sched[s.idx][d]])

        data["students"][token] = {
            "name": s.name,
            "school": s.school,
            "school_class": s.school_class,
            "category": s.category,
            "start": s.start_date.isoformat(),
            "end": s.end_date.isoformat(),
            "phone": s.phone,
            "email": s.email,
            "schedule": student_schedule,
            "stats": {
                "total_hours": round(total_hours, 1),
                "total_days": total_days,
                "activities_count": sum(len(asgs) for asgs in sched[s.idx].values()),
            },
        }

    out_path = Path(output_dir) / "web" / "data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return token_map, str(out_path)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Rozvrh praxí SK Slavia Praha")
    parser.add_argument("excel", help="Cesta k Excel souboru (Praxe 2026.xlsx)")
    parser.add_argument("--repre", help="CSV s repre konflikty (kategorie,od,do)", default=None)
    args = parser.parse_args()

    print("Načítám data...")
    wb = load_workbook(args.excel)

    activities = read_activities(wb["Program činností"])
    print(f"  Načteno {len(activities)} činností")

    students = read_students(wb["DBF studenti"])
    print(f"  Načteno {len(students)} studentů")

    if args.repre:
        load_repre_conflicts(args.repre, students)
        print(f"  Načteny repre konflikty z {args.repre}")

    print("Spouštím plánovací algoritmus...")
    sched, cap_usage, weekend_work = schedule(activities, students)

    print("Generuji doporučení pro TBD činnosti...")
    suggestions = suggest_tbd_dates(activities, students, sched)

    print("Zapisuji výstupní listy...")
    write_analysis_sheet(wb, students, activities, sched)
    write_matrix_sheet(wb, students, sched)
    write_detail_sheet(wb, students, sched)
    write_summary_sheet(wb, students, activities, sched, cap_usage, suggestions)

    wb.save(args.excel)
    print(f"Hotovo! Výstup zapsán do: {args.excel}")
    print(f"  → List 'Analýza potřeb' (PODKLAD PRO JEDNÁNÍ)")
    print(f"  → List 'Rozvrh - Matice'")
    print(f"  → List 'Rozvrh - Detail'")
    print(f"  → List 'Souhrn'")

    # JSON export for web portal
    excel_dir = str(Path(args.excel).parent)
    token_map, json_path = export_json(students, activities, sched, excel_dir)
    print(f"\n  → Web portál: {json_path}")
    print(f"\n  Tokeny pro studenty (URL: .../?t=TOKEN):")
    for s in students:
        print(f"    {s.name}: {token_map[s.idx]}")

    # Print quick summary
    print()
    for s in students:
        total_h = sum(a.hours for d, asgs in sched[s.idx].items() for a in asgs)
        days = len(sched[s.idx])
        gap = max(0, days * WORK_HOURS - total_h)
        flag = " ⚠" if gap > 0.5 else " ✓"
        print(f"  {s.name}: {total_h:.0f}h / {days * WORK_HOURS}h{flag}")


if __name__ == "__main__":
    main()
