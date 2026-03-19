# STATUS.md — Praxe 2026, SK Slavia Praha

> Poslední aktualizace: 2026-03-19

---

## Co bylo hotovo

### 1. Python skript s CLI (`rozvrh_praxe.py`)
- Čte vstupní Excel `Praxe 2026.xlsx` (listy "Program činností" a "DBF studenti")
- Algoritmicky přiřazuje činnosti studentům dle dostupnosti, kapacity a omezení (repre výjezdy, pracovní doba 8–15h, víkendy)
- Generuje 4 výstupní listy v Excelu (Analýza potřeb, Rozvrh-Matice, Rozvrh-Detail, Souhrn)
- Exportuje `data.json` pro webový portál
- Generuje unikátní přístupové tokeny (SHA-256 hash) pro každého studenta
- **CLI příkazy:** migrate, schedule, export, tokens, clone, list-students, list-activities, add-student, add-activity, legacy

### 2. SQLite databáze (`praxe.db`)
- Nahrazuje Excel jako primární úložiště dat
- Tabulky: season, activity, activity_date, student, repre_conflict, assignment, audit_log
- Multi-year podpora: každý ročník = záznam v tabulce `season`
- Kontaktní údaje (telefon, email) uloženy bezpečně jen v DB, nikdy v exportu
- Klonování sezón: `clone --from 2026 --to 2027` zkopíruje činnosti s TBD termíny
- Audit log: záznam všech změn

### 3. Webový portál pro studenty
- **Gate stránka** — chybová hláška při neplatném/chybějícím tokenu
- **Dashboard** — přehled dnešních aktivit, kompletní rozvrh, statistiky (hodiny, dny, počet činností)
- **Branding SK Slavia Praha** — barvy (červená #CC0000, tmavá, bílá), font Oswald, loga badge + hvězda
- **Mobilní optimalizace** — kartičkový layout pod 600px místo tabulky, dotykově přívětivé buttony
- **Tisk a export** — tlačítko Tisk (browser print) + Stáhnout HTML (standalone soubor s embedded styly)
- **Česká lokalizace** — české názvy měsíců, dnů, formátování dat

### 4. Nasazení na GitHub Pages
- Repository: [jirka-lang/AJA_SLAVIE_Praxe-2026](https://github.com/jirka-lang/AJA_SLAVIE_Praxe-2026)
- Live URL: https://jirka-lang.github.io/AJA_SLAVIE_Praxe-2026/
- Přístup studenta: `https://jirka-lang.github.io/AJA_SLAVIE_Praxe-2026/?t=TOKEN`

### 5. Dokumentace
- `CLAUDE.md` — technický průvodce pro budoucí instance Claude Code
- `STATUS.md` — tento soubor, přehled stavu projektu

### 6. Bezpečnost ✅
- **Kontakty odstraněny z `data.json`** — telefony, emaily i kontakty organizátorů
- **`pristupy_studentu.xlsx` odstraněn z git historie** (BFG/filter-repo)
- **`.gitignore`** — praxe.db, pristupy_studentu.xlsx nikdy v gitu
- Veřejně přístupný `data.json` obsahuje jen: jméno, škola, třída, kategorie, rozvrh, statistiky

---

## Co zbývá udělat

### Vysoká priorita — data a obsah
- [ ] **Upřesnit termíny činností** — řada aktivit v "Program činností" nemá potvrzený termín; domluvit s organizátory (ZŠ Eden, CSR, SKS aj.)
- [ ] **Doplnit repre kolize** — upřesnit termíny reprezentačních výjezdů U16–U20 a WU18 a zadat do Excelu
- [ ] **Aktualizovat rozvrh** — po doplnění dat: `migrate` → `schedule` → `export` → `git push`

### Střední priorita — distribuce
- [ ] **Doplnit emaily studentů** — zejména SOŠ Jarov
- [ ] **Rozeslat individuální URL odkazy** studentům (příkaz `tokens --season 2026`) emailem nebo přes skupinový chat
- [ ] **Testování na reálných mobilech** — ověřit portál na iOS Safari a Android Chrome

### Fáze 2 — Supabase + Admin UI (po sezóně 2026, pro 2027+)
- [ ] Migrace SQLite → Supabase (PostgreSQL, free tier) — identické schema
- [ ] Next.js admin panel na Vercelu — CZ rozhraní pro staff (CRUD studenti, činnosti, spuštění plánovače, export)
- [ ] GitHub Actions — spouštění Python scheduleru ze webu
- [ ] RLS politiky — kontakty viditelné jen pro adminy

### Nízká priorita / nice-to-have
- [ ] Vlastní doména (např. `praxe.skslavia.cz`) místo `jirka-lang.github.io`
- [ ] GitHub Actions workflow pro automatický rebuild po změně Excelu

---

## Jak aktualizovat rozvrh (workflow)

```bash
# 1. Upravit data v Excelu (listy "Program činností" / "DBF studenti"), uložit

# 2. Migrovat do databáze
cd "/Users/jirizemlicka/Library/Mobile Documents/com~apple~CloudDocs/AJA_AI_SLAVIE"
python3 rozvrh_praxe.py migrate "Praxe 2026.xlsx" --year 2026

# 3. Spustit plánovač
python3 rozvrh_praxe.py schedule --season 2026

# 4. Exportovat pro web
python3 rozvrh_praxe.py export --season 2026 --output web/data.json

# 5. Pushnout
cd web
git add data.json
git commit -m "Aktualizace rozvrhu"
git push

# GitHub Pages se automaticky aktualizuje (~30s)
```

---

## Přehled souborů

| Soubor | Účel | Umístění | Veřejný? |
|--------|------|----------|----------|
| `Praxe 2026.xlsx` | Zdrojová data (činnosti + studenti) | `/AJA_AI_SLAVIE/` | Ne |
| `rozvrh_praxe.py` | Generátor rozvrhu, CLI, DB správa | `/AJA_AI_SLAVIE/` | Ne |
| `praxe.db` | SQLite databáze (kontakty, rozvrhy, audit) | `/AJA_AI_SLAVIE/` | Ne |
| `web/index.html` | Hlavní HTML stránka portálu | GitHub repo | Ano |
| `web/app.js` | Frontend logika (auth, rendering) | GitHub repo | Ano |
| `web/style.css` | Styly + responsive + print | GitHub repo | Ano |
| `web/data.json` | Generovaná data pro frontend (bez kontaktů) | GitHub repo | Ano |
| `web/CLAUDE.md` | Technická dokumentace pro AI | GitHub repo | Ano |
| `web/STATUS.md` | Přehled stavu projektu | GitHub repo | Ano |

---

## Bezpečnostní stav

| Úroveň | Popis | Stav |
|--------|-------|------|
| 0 | Tokeny v URL (základní ochrana) | ✅ Hotovo |
| 1 | Kontakty odstraněny z data.json + git historie | ✅ Hotovo (2026-03-19) |
| 2 | Supabase + Admin UI (RLS, auth) | ⏳ Plánováno pro 2027 |
