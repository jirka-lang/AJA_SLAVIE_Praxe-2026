/* ── Praxe 2026 – Studentsky portal ──────────────────────────────────────── */

const CZ_DAYS = ["Ne", "Po", "Ut", "St", "Ct", "Pa", "So"];
const CZ_MONTHS = ["", "ledna", "unora", "brezna", "dubna", "kvetna",
    "cervna", "cervence", "srpna", "zari", "rijna", "listopadu", "prosince"];

function formatDateCZ(dateStr) {
    const d = new Date(dateStr + "T00:00:00");
    const day = CZ_DAYS[d.getDay()];
    return `${day} ${d.getDate()}.${d.getMonth() + 1}.`;
}

function formatDateLong(dateStr) {
    const d = new Date(dateStr + "T00:00:00");
    const day = CZ_DAYS[d.getDay()];
    return `${day} ${d.getDate()}. ${CZ_MONTHS[d.getMonth() + 1]} ${d.getFullYear()}`;
}

function todayISO() {
    const d = new Date();
    return d.getFullYear() + "-" +
        String(d.getMonth() + 1).padStart(2, "0") + "-" +
        String(d.getDate()).padStart(2, "0");
}

function activityTypeClass(type) {
    const t = (type || "").toLowerCase();
    if (t.includes("asisten") || t.includes("vypomoc")) return "type-asistence";
    if (t.includes("turnaj")) return "type-turnaj";
    if (t.includes("vyucov")) return "type-vyucovani";
    if (t.includes("prednas")) return "type-prednaska";
    if (t.includes("vzorov")) return "type-vzorova";
    if (t.includes("volno")) return "type-volno";
    return "type-default";
}

/* ── Init ────────────────────────────────────────────────────────────────── */

async function init() {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("t");

    let data;
    try {
        const resp = await fetch("data.json");
        if (!resp.ok) throw new Error("fetch failed");
        data = await resp.json();
    } catch (e) {
        showGate();
        return;
    }

    if (!token || !data.students[token]) {
        showGate();
        return;
    }

    const student = data.students[token];
    showDashboard(student, data);
}

function showGate() {
    document.getElementById("gate").classList.remove("hidden");
    document.getElementById("dashboard").classList.add("hidden");
}

function showDashboard(student, data) {
    document.getElementById("gate").classList.add("hidden");
    document.getElementById("dashboard").classList.remove("hidden");

    // Header
    document.getElementById("student-name").textContent = student.name;
    document.getElementById("student-meta").textContent =
        `${student.school} | ${student.category} | ${student.start} - ${student.end}`;

    // Last updated
    document.getElementById("last-updated").textContent = data.last_updated;

    renderToday(student);
    renderSchedule(student);
    renderStats(student);
}

/* ── Today ───────────────────────────────────────────────────────────────── */

function renderToday(student) {
    const today = todayISO();
    const titleEl = document.getElementById("today-title");
    const contentEl = document.getElementById("today-content");

    titleEl.textContent = `Dnes – ${formatDateLong(today)}`;

    const dayItems = student.schedule[today];
    if (!dayItems || dayItems.length === 0) {
        // Check if today is within practice period
        if (today >= student.start && today <= student.end) {
            contentEl.innerHTML = '<p class="today-none">Dnes nemas zadnou naplanovnou cinnost.</p>';
        } else {
            contentEl.innerHTML = '<p class="today-none">Dnes nemas praxi.</p>';
        }
        return;
    }

    const now = new Date();
    const currentMinutes = now.getHours() * 60 + now.getMinutes();

    let html = "";
    for (const item of dayItems) {
        const [startStr, endStr] = item.time.split("-");
        const [sh, sm] = startStr.split(":").map(Number);
        const [eh, em] = endStr.split(":").map(Number);
        const startMin = sh * 60 + sm;
        const endMin = eh * 60 + em;
        const isCurrent = currentMinutes >= startMin && currentMinutes < endMin;

        html += `
        <div class="today-item ${isCurrent ? "today-current" : ""}">
            <div class="today-time">${item.time}</div>
            <div>
                <div class="today-activity">
                    <span class="activity-pill ${activityTypeClass(item.type)}">${item.activity}</span>
                </div>
                ${item.organizer ? `<div class="today-detail">Organizator: ${item.organizer}</div>` : ""}
                ${item.contact ? `<div class="today-detail">Kontakt: ${item.contact}</div>` : ""}
            </div>
        </div>`;
    }
    contentEl.innerHTML = html;
}

/* ── Schedule table ──────────────────────────────────────────────────────── */

function renderSchedule(student) {
    const container = document.getElementById("schedule-table");
    const dates = Object.keys(student.schedule).sort();

    if (dates.length === 0) {
        container.innerHTML = '<p class="today-none">Zatim neni rozvrh k dispozici.</p>';
        return;
    }

    let html = '<table class="schedule-table"><thead><tr>';
    html += "<th>Cas</th><th>Cinnost</th><th>Organizator</th><th>Kontakt</th>";
    html += "</tr></thead><tbody>";

    for (const dateStr of dates) {
        html += `<tr class="day-header"><td colspan="4">${formatDateLong(dateStr)}</td></tr>`;
        for (const item of student.schedule[dateStr]) {
            const cls = activityTypeClass(item.type);
            html += `<tr>
                <td><strong>${item.time}</strong></td>
                <td><span class="activity-pill ${cls}">${item.activity}</span></td>
                <td>${item.organizer || ""}</td>
                <td>${item.contact || ""}</td>
            </tr>`;
        }
    }

    html += "</tbody></table>";
    container.innerHTML = html;
}

/* ── Stats ───────────────────────────────────────────────────────────────── */

function renderStats(student) {
    const container = document.getElementById("stats");
    const s = student.stats;

    const items = [
        { value: s.total_hours + "h", label: "Celkem hodin" },
        { value: s.total_days, label: "Dnu praxe" },
        { value: s.activities_count, label: "Cinnosti" },
    ];

    // Count unique activity types
    const types = new Set();
    for (const dayItems of Object.values(student.schedule)) {
        for (const item of dayItems) types.add(item.type);
    }
    items.push({ value: types.size, label: "Typu cinnosti" });

    container.innerHTML = items.map(i => `
        <div class="stat-box">
            <div class="stat-value">${i.value}</div>
            <div class="stat-label">${i.label}</div>
        </div>
    `).join("");
}

/* ── Print ───────────────────────────────────────────────────────────────── */

function printSchedule() {
    window.print();
}

/* ── Download HTML ───────────────────────────────────────────────────────── */

function downloadHTML() {
    const name = document.getElementById("student-name").textContent;
    const table = document.getElementById("schedule-table").innerHTML;
    const meta = document.getElementById("student-meta").textContent;

    const html = `<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<title>Rozvrh praxe – ${name}</title>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
body { font-family: "Inter", -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 0 1rem; color: #1A1A1A; }
.header { background: #1A1A1A; color: #fff; padding: 1rem 1.5rem; margin: 0 -1rem 0.25rem; display: flex; align-items: center; gap: 1rem; }
.header h1 { font-family: "Oswald", sans-serif; font-size: 1.4rem; font-weight: 700; letter-spacing: 0.1em; margin: 0; }
.header .sub { font-family: "Oswald", sans-serif; font-size: 0.75rem; color: #999; text-transform: uppercase; letter-spacing: 0.08em; }
.stripe { height: 4px; background: linear-gradient(90deg, #CC0000 50%, #fff 50%); margin: 0 -1rem 1.5rem; }
.meta { font-family: "Oswald", sans-serif; color: #6B6B6B; margin-bottom: 1.5rem; font-size: 0.95rem; letter-spacing: 0.03em; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th, td { padding: 0.5rem 0.75rem; border: 1px solid #D9D5D0; text-align: left; vertical-align: top; }
th { background: #CC0000; color: #fff; font-family: "Oswald", sans-serif; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
.day-header td { background: #1A1A1A; color: #fff; font-family: "Oswald", sans-serif; font-weight: 600; font-size: 0.9rem; }
.activity-pill { display: inline-block; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem; }
.type-asistence { background: #BDD7EE; }
.type-turnaj { background: #F8CBAD; }
.type-vyucovani { background: #C6EFCE; }
.type-prednaska { background: #D9E2F3; }
.type-vzorova { background: #FCE4D6; }
.type-volno { background: #F2F2F2; }
.type-default { background: #eee; }
.footer { text-align: center; margin-top: 2rem; padding: 1rem; border-top: 1px solid #D9D5D0; color: #aaa; font-family: "Oswald", sans-serif; font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; }
</style>
</head>
<body>
<div class="header">
    <div><h1>PRAXE 2026</h1><div class="sub">SK Slavia Praha &mdash; Oddil mladeze</div></div>
</div>
<div class="stripe"></div>
<p class="meta">${name} &mdash; ${meta}</p>
${table}
<div class="footer">SK Slavia Praha &mdash; Oddil mladeze &mdash; Praxe 2026</div>
</body>
</html>`;

    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rozvrh-praxe-${name.replace(/\s+/g, "-").toLowerCase()}.html`;
    a.click();
    URL.revokeObjectURL(url);
}

/* ── Start ───────────────────────────────────────────────────────────────── */

document.addEventListener("DOMContentLoaded", init);
