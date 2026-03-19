# STATUS.md — Praxe 2026, SK Slavia Praha

> Poslední aktualizace: 2026-03-19

---

## Co bylo hotovo

### 1. Python skript pro generování rozvrhu (`rozvrh_praxe.py`)
- Čte vstupní Excel `Praxe 2026.xlsx` (listy "Program činností" a "DBF studenti")
- Algoritmicky přiřazuje činnosti studentům dle dostupnosti, kapacity a omezení (repre výjezdy, pracovní doba 8–15h, víkendy)
- Generuje 4 výstupní listy v Excelu (Analýza potřeb, Rozvrh-Matice, Rozvrh-Detail, Souhrn)
- Exportuje `data.json` pro webový portál
- Generuje unikátní přístupové tokeny (MD5 hash) pro každého studenta

### 2. Webový portál pro studenty
- **Gate stránka** — chybová hláška při neplatném/chybějícím tokenu
- **Dashboard** — přehled dnešních aktivit, kompletní rozvrh, statistiky (hodiny, dny, počet činností)
- **Branding SK Slavia Praha** — barvy (červená #CC0000, tmavá, bílá), font Oswald, loga badge + hvězda
- **Mobilní optimalizace** — kartičkový layout pod 600px místo tabulky, dotykově přívětivé buttony
- **Tisk a export** — tlačítko Tisk (browser print) + Stáhnout HTML (standalone soubor s embedded styly)
- **Česká lokalizace** — české názvy měsíců, dnů, formátování dat

### 3. Nasazení na GitHub Pages
- Repository: [jirka-lang/AJA_SLAVIE_Praxe-2026](https://github.com/jirka-lang/AJA_SLAVIE_Praxe-2026)
- Live URL: https://jirka-lang.github.io/AJA_SLAVIE_Praxe-2026/
- Přístup studenta: `https://jirka-lang.github.io/AJA_SLAVIE_Praxe-2026/?t=TOKEN`

### 4. Excel s přístupovými odkazy (`pristupy_studentu.xlsx`)
- 18 studentů s klikacími hyperlinky na jejich osobní dashboard
- Sloupce: Jméno, Škola, Telefon, Email, Token, Přístupový odkaz
- ⚠️ Soubor obsahuje kontaktní údaje — uchovávat pouze interně, nesdílet veřejně

### 5. Dokumentace
- `CLAUDE.md` — technický průvodce pro budoucí instance Claude Code
- `STATUS.md` — tento soubor, přehled stavu projektu

### 6. Bezpečnost — Úroveň 1 ✅ (2026-03-19)
- **Odstraněny telefony a emaily z `data.json`** — kontaktní údaje zůstaly pouze v interním `pristupy_studentu.xlsx`
- Veřejně přístupný `data.json` nyní obsahuje jen: jméno, škola, třída, kategorie, rozvrh, statistiky
- Aktualizován `rozvrh_praxe.py` — budoucí exporty automaticky vynechají kontaktní pole

---

## Co zbývá udělat

### Vysoká priorita — data a obsah
- [ ] **Upřesnit termíny činností** — řada aktivit v "Program činností" nemá potvrzený termín; domluvit s organizátory (ZŠ Eden, CSR, SKS aj.)
- [ ] **Doplnit repre kolize** — upřesnit termíny reprezentačních výjezdů U16–U20 a WU18 a zadat do Excelu
- [ ] **Aktualizovat rozvrh** — po doplnění dat spustit skript a pushnout nový `data.json`

### Střední priorita — distribuce
- [ ] **Doplnit emaily studentů** — zejména SOŠ Jarov (potřeba pro Úroveň 2 bezpečnosti a pro rozesílání odkazů)
- [ ] **Rozeslat individuální URL odkazy** studentům (z `pristupy_studentu.xlsx`) emailem nebo přes skupinový chat
- [ ] **Testování na reálných mobilech** — ověřit portál na iOS Safari a Android Chrome

### Bezpečnost — Úroveň 2 (doporučeno před spuštěním)
- [ ] **Přesunout hosting na Cloudflare Pages** (propojení s GitHub repo, zdarma)
- [ ] **Zapnout Cloudflare Access** — ochrana portálu přihlášením přes email + jednorázový PIN kód
- [ ] **Přidat emaily studentů** do povolené skupiny v Cloudflare Access
- *Prerekvizita: účet na Cloudflare + emaily studentů*

### Nízká priorita / nice-to-have
- [ ] Vlastní doména (např. `praxe.skslavia.cz`) místo `jirka-lang.github.io`
- [ ] GitHub Actions workflow pro automatický rebuild po změně Excelu
- [ ] Admin rozhraní pro editaci bez Excelu

---

## Jak aktualizovat rozvrh (workflow)

```bash
# 1. Upravit data v Excelu (listy "Program činností" / "DBF studenti"), uložit

# 2. Spustit skript
cd "/Users/jirizemlicka/Library/Mobile Documents/com~apple~CloudDocs/AJA_AI_SLAVIE"
python3 rozvrh_praxe.py "Praxe 2026.xlsx"

# 3. Pushnout
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
| `rozvrh_praxe.py` | Generátor rozvrhu a data.json | `/AJA_AI_SLAVIE/` | GitHub |
| `web/index.html` | Hlavní HTML stránka portálu | GitHub repo | Ano |
| `web/app.js` | Frontend logika (auth, rendering) | GitHub repo | Ano |
| `web/style.css` | Styly + responsive + print | GitHub repo | Ano |
| `web/data.json` | Generovaná data pro frontend (bez kontaktů) | GitHub repo | Ano |
| `web/pristupy_studentu.xlsx` | Excel s přístupovými odkazy a kontakty | GitHub repo | ⚠️ Ano* |
| `web/CLAUDE.md` | Technická dokumentace pro AI | GitHub repo | Ano |
| `STATUS.md` | Tento soubor | `/AJA_AI_SLAVIE/` + GitHub | Ano |

*\* `pristupy_studentu.xlsx` je aktuálně veřejně dostupný na GitHub — zvážit přesun mimo repo nebo přejít na Úroveň 2.*

---

## Bezpečnostní stav

| Úroveň | Popis | Stav |
|--------|-------|------|
| 0 | Tokeny v URL (základní ochrana) | ✅ Hotovo |
| 1 | Kontakty odstraněny z data.json | ✅ Hotovo (2026-03-19) |
| 2 | Cloudflare Access (email + PIN) | ⏳ Naplánováno |
| 3 | Backend API (data neveřejná) | 💡 Budoucnost |
