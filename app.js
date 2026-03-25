/* ── Praxe 2026 – Studentsky portal (live Supabase) ─────────────────────── */

const SUPABASE_URL = "https://vudxgsnonafdlmivthlw.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ1ZHhnc25vbmFmZGxtaXZ0aGx3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4OTE5MjIsImV4cCI6MjA4OTQ2NzkyMn0.wxUxG0lNZI12X0k8pAmKek8OtvBuDPThxmRLBtQvMNM";

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

    if (!token) {
        showGate();
        return;
    }

    try {
        // Volání Supabase RPC funkce — vrátí rozvrh přímo z databáze
        const resp = await fetch(
            `${SUPABASE_URL}/rest/v1/rpc/get_student_schedule`,
            {
                method: "POST",
                headers: {
                    "apikey": SUPABASE_ANON_KEY,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ student_token: token }),
            }
        );

        if (!resp.ok) throw new Error("fetch failed");

        const data = await resp.json();

        if (!data || !data.student) {
            showGate();
            return;
        }

        showDashboard(data);
    } catch (e) {
        // Fallback na statický data.json (offline/backup)
        try {
            const resp = await fetch("data.json");
            if (!resp.ok) throw new Error("fallback failed");
            const fallbackData = await resp.json();

            if (!fallbackData.students[token]) {
                showGate();
                return;
            }

            // Převeď starý formát na nový
            const s = fallbackData.students[token];
            showDashboard({
                student: { name: s.name, school: s.school, school_class: s.school_class, category: s.category, start: s.start, end: s.end },
                schedule: s.schedule,
                stats: s.stats,
                last_updated: fallbackData.last_updated,
                period: fallbackData.period,
            });
        } catch {
            showGate();
        }
    }
}

function showGate() {
    document.getElementById("gate").classList.remove("hidden");
    document.getElementById("dashboard").classList.add("hidden");
}

function showDashboard(data) {
    document.getElementById("gate").classList.add("hidden");
    document.getElementById("dashboard").classList.remove("hidden");

    const student = data.student;

    // Header
    document.getElementById("student-name").textContent = student.name;
    document.getElementById("student-meta").textContent =
        `${student.school} | ${student.category} | ${student.start} - ${student.end}`;

    // Last updated
    document.getElementById("last-updated").textContent = data.last_updated;

    renderToday(data);
    renderSchedule(data);
    renderStats(data);
}

/* ── Today ───────────────────────────────────────────────────────────────── */

function renderToday(data) {
    const today = todayISO();
    const titleEl = document.getElementById("today-title");
    const contentEl = document.getElementById("today-content");

    titleEl.textContent = `Dnes – ${formatDateLong(today)}`;

    const dayItems = data.schedule[today];
    if (!dayItems || dayItems.length === 0) {
        if (today >= data.student.start && today <= data.student.end) {
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
            </div>
        </div>`;
    }
    contentEl.innerHTML = html;
}

/* ── Schedule table ──────────────────────────────────────────────────────── */

function renderSchedule(data) {
    const tableContainer = document.getElementById("schedule-table");
    const cardsContainer = document.getElementById("schedule-cards");
    const dates = Object.keys(data.schedule).sort();

    if (dates.length === 0) {
        tableContainer.innerHTML = '<p class="today-none">Zatim neni rozvrh k dispozici.</p>';
        return;
    }

    // Desktop: table view
    let table = '<table class="schedule-table"><thead><tr>';
    table += "<th>Cas</th><th>Cinnost</th><th>Organizator</th>";
    table += "</tr></thead><tbody>";

    // Mobile: card view
    let cards = "";

    for (const dateStr of dates) {
        const dayLabel = formatDateLong(dateStr);

        table += `<tr class="day-header"><td colspan="3">${dayLabel}</td></tr>`;
        cards += `<div class="mobile-day-header">${dayLabel}</div>`;

        for (const item of data.schedule[dateStr]) {
            const cls = activityTypeClass(item.type);

            table += `<tr>
                <td><strong>${item.time}</strong></td>
                <td><span class="activity-pill ${cls}">${item.activity}</span></td>
                <td>${item.organizer || ""}</td>
            </tr>`;

            cards += `<div class="mobile-activity">
                <div class="mobile-activity-time">${item.time}</div>
                <div class="mobile-activity-name">
                    <span class="activity-pill ${cls}">${item.activity}</span>
                </div>
                <div class="mobile-activity-meta">
                    ${item.organizer ? `<span>Organizator: ${item.organizer}</span>` : ""}
                </div>
            </div>`;
        }
    }

    table += "</tbody></table>";

    tableContainer.innerHTML = table;
    cardsContainer.className = "schedule-cards";
    cardsContainer.innerHTML = cards;
}

/* ── Stats ───────────────────────────────────────────────────────────────── */

function renderStats(data) {
    const container = document.getElementById("stats");
    const s = data.stats;

    const items = [
        { value: s.total_hours + "h", label: "Celkem hodin" },
        { value: s.total_days, label: "Dnu praxe" },
        { value: s.activities_count, label: "Cinnosti" },
    ];

    // Count unique activity types
    const types = new Set();
    for (const dayItems of Object.values(data.schedule)) {
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
