# Official Data Ingestion & Methodology Guide — THE UNHEARD

Last updated: `2026-11-11`  
Primary Custodian: **National Crime Records Bureau (NCRB), Ministry of Home Affairs, Government of India**

---

## 1. Official Data Availability Audit

| Publication | Geographic Granularity | Primary Rape (Sec. 376 IPC) Metrics | Crime Against Women (CAW) Totals | Disposal & Conviction Metrics | Status in `data/raw/` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Crime in India 2023** | National snapshot only (`9-2023.pdf`), State/UT Total Population (`6Population2023.pdf`) | Unavailable in downloadable NCRB 2023 Chapter 3A Excel tables (`crime-in-india-table-content.html?year=2023` returns 0 tables) | National CAW total: `448,211` cases (`66.2` per lakh female population) extracted from official snapshot `9-2023.pdf` | Pending official Chapter 3A Table 3A.5–3A.8 release | **Partially Available** — PDFs preserved in `data/raw/ncrb_2023/`. Granular 2023 Sec. 376 Rape rows are explicitly marked *Unavailable* until official tables are released or manually imported. |
| **Crime in India 2022** | 28 States, 8 UTs, All-India | `I` (Cases), `V` (Victims), `R` (Rate per lakh female pop.), Age groups, Offender relation, Sec. 376(1)/(2) breakdown | State/UT CAW 2020–2022 (`TABLE 3A.1`) | National Rape Police & Court Disposal (`3A.5`, `3A.7`); State/UT Total CAW Disposal (`3A.6`, `3A.8`) | **Complete** (`data/raw/ncrb_2022/`, 11 files) |
| **Crime in India 2021** | 28 States, 8 UTs, All-India | `I`, `V`, `R`, Age groups, Offender relation, Section-wise | State/UT CAW 2019–2021 (`TABLE 3A.1`) | National Rape Police & Court Disposal (`3A.5`, `3A.7`); State/UT Total CAW Disposal (`3A.6`, `3A.8`) | **Complete** (`data/raw/ncrb_2021/`, 9 files) |
| **Crime in India 2020** | 28 States, 8 UTs, All-India | `I`, `V`, `R` (`TABLE 3A.2`), Section-wise (`3A.11`); Age & Offender relation in PDF (`3A.3`, `3A.4`) | State/UT CAW 2018–2020 (`TABLE 3A.1`) | National Rape Police & Court Disposal (`3A.5`, `3A.7`); State `3A.6`/`3A.8` were 0-byte on NCRB | **Mostly Complete** (`data/raw/ncrb_2020/`, 7 files) |

---

## 2. Critical Statistical & Legal Caveats

1. **Reported FIRs vs. Actual Prevalence:** NCRB compiles First Information Reports (FIRs) registered by State/UT Police under the *Principal Offence Rule* (if a single FIR includes multiple offences, it is classified under the offence carrying the highest penalty). Counts reflect **police-recorded reporting**, NOT true societal prevalence or victim survey incidence. High counts or rates can indicate higher reporting willingness and institutional access rather than higher underlying incidence.
2. **Cases (`I`) vs. Female Victims (`V`):** NCRB Table 3A.2 explicitly separates `I` (Number of Incidences/Cases) from `V` (Number of Female Victims). A single case may involve multiple victims (`V >= I`). Both are stored separately and never summed or conflated.
3. **Rape (Sec. 376 IPC) vs. Total Crime Against Women vs. POCSO Child Rape:**
   - `TABLE 3A.2` separates **Rape (Sec. 376 IPC)** (`I`, `V`, `R`), **Attempt to Commit Rape (Sec. 376/511 IPC)**, **Murder with Rape/Gang Rape**, **Child Rape under POCSO Act (Sec. 4 & 6)**, and **Total Crime Against Women (IPC + SLL)**.
   - **Disposal Granularity Warning:** NCRB publishes **Rape-specific** police and court disposal nationally (`TABLE 3A.5` and `TABLE 3A.7`), whereas State/UT-level disposal (`TABLE 3A.6` and `TABLE 3A.8`) covers **Total Crime Against Women**, NOT Rape alone. The platform strictly prevents presenting CAW state disposal rates as Rape state disposal rates.
4. **Population Denominators & Rate Formula:**
   - NCRB computes Crime Against Women and Sec. 376 Rape rates per 100,000 **Mid-Year Projected Female Population** (`(Cases / Projected_Female_Pop_Lakhs)` where 1 Lakh = 100,000), sourced from the Registrar General of India / MoHFW *Report of the Technical Group on Population Projections* and printed directly in `TABLE 3A.1`.
   - `6Population2023.pdf` reports **total** projected population (both sexes), which is tagged `denominator_scope = "total"` and is NEVER used as the denominator for female-only crime rates.
5. **Legal Classification Shifts (2013 & 2024):**
   - **2013 (Criminal Law Amendment Act, 2013):** Expanded statutory definition of rape under IPC Sec. 375/376 after April 2013; pre-2013 and post-2013 series are non-comparable.
   - **2024 (Bharatiya Nyaya Sanhita — BNS, 2023, effective 1 July 2024):** Replaced IPC Sec. 375/376 with BNS Sec. 63–71. Multi-year comparisons crossing 2024 must flag the IPC-to-BNS transition.
6. **Administrative & Boundary Changes (2019–2020):**
   - **31 Oct 2019:** Erstwhile State of Jammu & Kashmir was reorganized into UT of Jammu & Kashmir (`J&K`) and UT of Ladakh (`*` / `@` markers in NCRB 2018–2020 tables).
   - **26 Jan 2020:** UT of Dadra & Nagar Haveli and UT of Daman & Diu merged into Dadra & Nagar Haveli and Daman & Diu (`+` marker in NCRB 2018–2020 tables).

---

## 3. Reproducible Ingestion & Manual Import Workflow

All files in `data/raw/` remain strictly read-only. Derived normalized CSV exports are written to `data/processed/` and persisted into SQLite (`backend/the_unheard.db`) via versioned, idempotent ingestion runs.

### Standard Re-Ingestion (All Registered Sources)
```powershell
cd backend
.\.venv\Scripts\python.exe -m app.ingestion.run
```

### Manual Import Workflow (e.g., When NCRB Publishes 2023 Chapter 3A Excel Files)
1. Place the official downloaded `.xlsx` or `.csv` file inside `data/raw/ncrb_<year>/` without modifying existing files.
2. Add or pass the official metadata and run:
```powershell
cd backend
.\.venv\Scripts\python.exe -m app.ingestion.run --manual-file ..\data\raw\ncrb_2023\TABLE3A2.xlsx --table-code "TABLE 3A.2" --year 2023 --source-url "https://www.ncrb.gov.in/..."
```
3. The pipeline automatically computes the SHA-256 checksum, skips duplicate dataset versions unless `--force` is passed, normalizes State/UT names to `GeographicUnit`, runs statistical validation rules, logs `DataQualityIssue` records, and updates `data/processed/`.

