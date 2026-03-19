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

### 5. Dokumentace
- `CLAUDE.md` — technický průvodce pro budoucí instance Claude Code

---

## Co zbývá udělat

### Vysoká priorita
- [ ] **Upřesnit termíny činností** — řada aktivit v "Program činností" nemá potvrzený termín; je potřeba je domluvit s organizátory (ZŠ Eden, CSR, SKS aj.)
- [ ] **Doplnit repre kolize** — upřesnit termíny reprezentačních výjezdů U16–U20 a WU18 a zadat je do Excelu
- [ ] **Doplnit kontaktní údaje studentů** — většina studentů ze SOŠ Jarov nemá telefon ani email
- [ ] **Aktualizovat rozvrh** — po doplnění dat znovu spustit `python3 rozvrh_praxe.py "Praxe 2026.xlsx"` a pushnout nový `data.json`

### Střední priorita
- [ ] **Distribuce odkazů studentům** — rozeslat individuální URL odkazy (z `pristupy_studentu.xlsx`) emailem nebo přes skupinový chat
- [ ] **Testování na reálných mobilech** — ověřit portál na iOS Safari a Android Chrome
- [ ] **Vlastní doména** — zvážit CNAME pro GitHub Pages (např. `praxe.skslavia.cz`) místo `jirka-lang.github.io`

### Nízká priorita / nice-to-have
- [ ] **Push notifikace** — upozornění na změny rozvrhu (vyžaduje backend)
- [ ] **Automatický refresh dat** — GitHub Actions workflow pro automatický rebuild po push do Excelu
- [ ] **Admin rozhraní** — webový formulář pro editaci činností bez nutnosti otevírat Excel

---

## Jak aktualizovat rozvrh (workflow)

```
1. Upravit data v "Praxe 2026.xlsx" (listy Program činností / DBF studenti)
2. Uložit Excel
3. Spustit:
   cd "/Users/jirizemlicka/Library/Mobile Documents/com~apple~CloudDocs/AJA_AI_SLAVIE"
   python3 rozvrh_praxe.py "Praxe 2026.xlsx"
4. Zkopírovat výstup do webu:
   cp data.json web/
5. Pushnout:
   cd web && git add data.json && git commit -m "Aktualizace rozvrhu" && git push
6. GitHub Pages se automaticky aktualizuje (~30s)
```

---

## Přehled souborů

| Soubor | Účel | Umístění |
|--------|------|----------|
| `Praxe 2026.xlsx` | Zdrojová data (činnosti + studenti) | `/AJA_AI_SLAVIE/` |
| `rozvrh_praxe.py` | Generátor rozvrhu a data.json | `/AJA_AI_SLAVIE/` |
| `web/index.html` | Hlavní HTML stránka portálu | GitHub repo |
| `web/app.js` | Frontend logika (auth, rendering) | GitHub repo |
| `web/style.css` | Styly + responsive + print | GitHub repo |
| `web/data.json` | Generovaná data pro frontend | GitHub repo |
| `web/pristupy_studentu.xlsx` | Excel s přístupovými odkazy | GitHub repo |
| `web/CLAUDE.md` | Technická dokumentace pro AI | GitHub repo |
