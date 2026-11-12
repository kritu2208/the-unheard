# THE UNHEARD

> **"Behind every number, there is a story."**  
> A single-page investigative crime data analytics dashboard examining reported crimes against women and children in India through official National Crime Records Bureau (NCRB) *Crime in India* Chapter 3A records (2018–2023).

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-success?style=for-the-badge&logo=vercel)](https://the-unheard-la3sor1qq-krucki-gang.vercel.app/)
[![Backend Status](https://img.shields.io/badge/Backend-Render-blue?style=for-the-badge&logo=render)](https://the-unheard.onrender.com/api/health)
[![Official Data](https://img.shields.io/badge/Data%20Source-NCRB%20Chapter%203A-critical?style=for-the-badge)](https://ncrb.gov.in/)

---

## 🔗 Live Application

- **Live Dashboard:** [https://the-unheard-la3sor1qq-krucki-gang.vercel.app/](https://the-unheard-la3sor1qq-krucki-gang.vercel.app/)
- **Backend API:** [https://the-unheard.onrender.com/api](https://the-unheard.onrender.com/api)

---

## 🔍 Key Analytical Findings & Jurisdictional Distribution

Official NCRB records reveal stark contrasts depending on whether one looks at **absolute registered case volumes** (driven by population size) or **population-adjusted crime rates per 100,000 females**:

### 1. Reported Rape Cases (Sec. 376 IPC — 2022)
- **Highest by Absolute FIR Volume (Cases):**
  1. **Rajasthan**: **5,399 cases** (#1 in India — 17.1% of national total)
  2. **Uttar Pradesh**: **3,690 cases** (#2)
  3. **Madhya Pradesh**: **3,029 cases** (#3)
  4. **Maharashtra**: **2,904 cases** (#4)
  5. **Haryana**: **1,787 cases** (#5)
  6. **Odisha**: **1,464 cases** (#6)
- **Highest by Population Rate (per 100k Female Population):**
  1. **Uttarakhand**: **15.4** per 100k females
  2. **Chandigarh (UT)**: **13.9** per 100k females
  3. **Rajasthan**: **13.8** per 100k females
  4. **Haryana**: **12.7** per 100k females
  5. **Delhi (NCT)**: **12.3** per 100k females
  *(National Average: **4.7** per 100,000 females)*
- **Lowest Reported Cases (2022):**
  - **Lakshadweep**: 4 cases | **Ladakh**: 5 cases | **Nagaland**: 7 cases | **Puducherry**: 9 cases | **D&NH and D&D**: 9 cases.

---

### 2. Total Crimes Against Women (All CAW Heads Combined — 2022)
- **Highest by Absolute Volume (445,256 National Total):**
  1. **Uttar Pradesh**: **65,743 cases** (14.8% of All-India CAW)
  2. **Maharashtra**: **45,331 cases** (10.2%)
  3. **Rajasthan**: **45,058 cases** (10.1%)
  4. **West Bengal**: **34,738 cases** (7.8%)
  5. **Madhya Pradesh**: **32,765 cases** (7.4%)
- **Highest by CAW Rate per 100k Females:**
  1. **Delhi (NCT)**: **144.4** per 100k females (#1 highest reporting intensity)
  2. **Haryana**: **118.7** per 100k females
  3. **Telangana**: **117.0** per 100k females
  4. **Rajasthan**: **115.1** per 100k females
  5. **Odisha**: **103.3** per 100k females
  *(National Average: **66.4** per 100,000 females)*

---

### 3. Judicial & Investigation Findings (2020–2022)
- **Police Chargesheet Rate:** **77.9%** nationally (Police complete investigation and file formal charges in roughly 7 out of 8 cases).
- **Court Conviction Rate:** **27.4%** nationally (Only ~1 in 4 concluded trials results in conviction).
- **Trial Pendency Rate:** **90.0%** of active court cases remain pending trial year-on-year.
- **Survivor-Offender Relationship (Table 3A.4):** In **96.8%** of registered Sec. 376 rape cases, the accused was a person **known to the survivor** (family, intimate partner, neighbor, or acquaintance).

> **Statutory Analytical Warning:** High FIR registration in states like Rajasthan or Delhi often reflects **mandatory FIR registration drives, greater civil awareness, and active police reporting assistance**, whereas lower counts in certain regions can reflect systemic under-reporting and societal stigma rather than greater objective safety.

---

## 📖 Key Terms & Abbreviations Explained

When analyzing official crime statistics in India, terminological precision is essential to avoid misinterpretation:

| Term / Abbreviation | Full Form & Legal Definition | Significance in Analysis |
| :--- | :--- | :--- |
| **CAW** | **Crimes Against Women** | Broad statutory umbrella encompassing all IPC crimes against women (Rape, Cruelty by Husband/Relatives, Kidnapping, Dowry Deaths, Assault) plus Special and Local Laws (SLL). **Never conflated with Rape alone.** |
| **Sec. 376 IPC** | **Section 376 Indian Penal Code** | The specific statutory section governing rape offences in India (broadened post-2013 Criminal Law Amendment; transitioned to Sections 63–71 of the Bharatiya Nyaya Sanhita / BNS effective 1 July 2024). |
| **NCRB** | **National Crime Records Bureau** | Attached office of the Ministry of Home Affairs (MHA), Government of India, responsible for collecting and compiling national crime records under the annual *Crime in India* publication. |
| **Cases (I)** | **Registered Police Cases (Incidents / FIRs)** | Number of First Information Reports (FIRs) officially registered by police departments. |
| **Victims (V)** | **Number of Survivors / Victims** | Actual count of individual survivors involved in registered cases. A single case/FIR can involve multiple victims ($V \ge I$). |
| **Rate per 100k** | **Crime Rate per 100,000 Female Population** | $\text{Rate} = \frac{\text{Reported Cases}}{\text{Projected Mid-Year Female Population (in Lakhs)}}$. Calculated strictly using Registrar General of India (RGI) census projections. |
| **Principal Offence Rule** | **NCRB Counting Rule** | When a single incident involves multiple offences (e.g. Rape and Murder), it is counted **only once** under the offence carrying the highest statutory penalty. |
| **Chargesheet Rate (%)** | **Police Investigation Completion** | Percentage of investigated cases where the police filed a formal chargesheet in court out of total cases where investigation was completed. |
| **Conviction Rate (%)** | **Judicial Outcome** | Percentage of completed court trials resulting in conviction out of total trials completed that year. |
| **Trial Pendency (%)** | **Judicial Congestion** | Percentage of active court cases awaiting completion of trial at the end of the reporting year. |

---

## 📸 Dashboard Walkthrough

### 1. Masthead, Active Filters & KPI Strip
![Hero & KPI Overview](docs/screenshots/01_hero_overview.jpg)
- **Top Filter Navigation:** Real-time selector for reporting year (2018–2023), state/UT jurisdiction, and active metrics.
- **Export Toolbar:** 1-click downloads for **CSV data extracts**, **MD analytical summaries**, and **strict 1-page A4 landscape PDF briefs**.
- **Executive KPIs:** Distinct breakdown of Reported Sec. 376 FIRs (31,516), Female Victims & Rate per 100k (31,982 · 4.7), broader CAW FIRs (445,256), and National Chargesheet / Conviction rates (77.9% / 27.4%).

---

### 2. Longitudinal Trajectory & Judicial Attrition
![Longitudinal Trajectory and Disposal](docs/screenshots/02_trend_disposal.jpg)
- **All-India Longitudinal Trajectory (2020–2022):** Tracks reported cases with annotations for the 2020 COVID-19 nationwide mobility lockdown contraction and subsequent resumption of station reporting.
- **Disposal & Judicial Attrition Chart:** Grouped bar visualization comparing high police chargesheet rates (~77%) against actual judicial convictions (~27%) alongside persistent 90% court trial pendency.

---

### 3. State Intensity Matrix & Comparative Ranking
![State Matrix and Rankings](docs/screenshots/03_state_matrix_ranking.png)
- **State/UT Intensity Matrix:** Interactive 36-jurisdiction grid displaying reporting intensity tiles; clicking any state immediately isolates that jurisdiction across all charts.
- **State Rankings Bar Chart:** Ordered bar chart for the active metric (e.g., Rajasthan, Uttar Pradesh, Madhya Pradesh) accompanied by statutory reminders that higher FIR counts reflect registration accessibility rather than true safety rankings.

---

### 4. Side-by-Side Jurisdictional Comparison
![State Comparison Panel](docs/screenshots/04_state_comparison.png)
- Direct side-by-side indicator comparison between any two States/UTs (e.g., Rajasthan vs. Maharashtra) normalizing reported counts against projected female population denominators (Lakhs).

---

## 🛠️ Architecture & Tech Stack

```
THE-UNHEARD/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # FastAPI REST endpoints (/dashboard, /research, /health)
│   │   ├── services/          # Statistical calculation & PDF vector rendering
│   │   ├── models/            # SQLAlchemy database models
│   │   └── ingestion/         # Official Excel & PDF tabular parsers
│   ├── the_unheard.db         # Bundled SQLite database (6,520 verified records)
│   └── requirements.txt       # Python dependencies (FastAPI, ReportLab, SQLAlchemy, Pandas)
├── frontend/
│   ├── src/
│   │   ├── charts/            # Recharts implementations (Trend, Bar, Disposal)
│   │   ├── components/        # Masthead, KPI strips, State comparisons, Footer
│   │   └── services/api.ts    # Centralized API service with cloud base URL
│   ├── tailwind.config.js     # Dark editorial charcoal & crimson palette
│   └── package.json           # React 18, Vite, TypeScript, Tailwind
└── docs/screenshots/          # High-resolution dashboard walkthrough images
```

---

## 🚀 Local Development Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ & npm

### 2. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## ⚖️ Methodological Safeguards & Ethical Notice

1. **Reporting vs. Societal Incidence:** Official NCRB figures capture police-registered FIRs. An increase in registered numbers often indicates higher reporting willingness, better registration enforcement, or NGO assistance, rather than an increase in crime.
2. **Denominators Matter:** High absolute counts correlate with total population. Crime rates must always be evaluated per 100,000 females using official census denominators.
3. **Data Availability Boundary:** While NCRB released 2023 national totals (`9-2023.pdf`), granular state-level Sec. 376 spreadsheets remain unreleased by NCRB; 2022 remains the latest verified state edition.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE). Official crime data is sourced from public NCRB publications under the Government of India Open Data directives.
