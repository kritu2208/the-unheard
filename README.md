# THE UNHEARD

> **"Behind every number, there is a story."**  
> A single-page investigative data analytics dashboard examining reported crimes against women and children in India through official National Crime Records Bureau (NCRB) *Crime in India* Chapter 3A records (2018–2023).

---

## Overview

**THE UNHEARD** presents official Indian crime data with statistical rigor, statutory transparency, and editorial clarity. Built as an interactive single-page dashboard, it avoids sensationalism and enforces strict methodological safeguards (such as the *Principal Offence Rule* and separation of reported FIRs from victim counts).

- **Data Source:** Verified official NCRB *Crime in India* Chapter 3A publications (2018–2023).
- **Format:** Single-page analytics dashboard with real-time filters and multi-format exports.
- **Design:** Dark investigative editorial aesthetic inspired by premium data journalism.

---

## Core Capabilities

- **Strict Data Hierarchy & Provenance**:
  - Separates **Registered Cases (I)** from **Female Victims (V)** (a single FIR can involve multiple victims).
  - Normalizes jurisdictional rates per 100,000 females using official RGI projected mid-year census estimates.
  - Keeps Rape (Sec. 376 IPC) distinct from Total Crime Against Women (IPC+SLL).
- **Longitudinal Trend Tracking**:
  - Trajectory tracking across 2020–2022 with COVID-19 mobility impact annotations.
- **Judicial Attrition & Disposal Analysis**:
  - Evaluates police chargesheet rate (77.9%), court conviction rate (27.4%), and trial pendency rates (90.0%).
- **Interactive Global Filtering**:
  - Real-time updates across reporting year, state/UT jurisdiction, and active metrics.
- **Export Engine**:
  - **PDF Brief**: Strict 1-page A4 landscape executive briefing document.
  - **CSV**: Filter-aware flat data extract with citations and notes.
  - **Markdown (MD)**: Structured executive summary for reporters and researchers.

---

## Tech Stack

- **Frontend**:
  - React 18 & TypeScript
  - Tailwind CSS (Dark Editorial Theme)
  - Recharts (Interactive longitudinal, bar, and disposal visualizations)
  - Lucide React (Minimal iconography)
  - Vite
- **Backend**:
  - Python 3.11+ / FastAPI
  - SQLite & SQLAlchemy ORM
  - ReportLab (Exact 1-page A4 landscape vector PDF generation)
  - Pandas & OpenPyXL (Official Excel & PDF ingestion pipeline)
  - PyTest

---

## Getting Started

### 1. Prerequisites
- Node.js 18+ and npm
- Python 3.10+

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Backend API will be available at `http://127.0.0.1:8000` (Swagger docs at `/docs`).

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## Methodological Boundaries & Notes

1. **Principal Offence Rule**: In multi-offence criminal incidents, NCRB records the case only under the offence carrying the highest statutory penalty.
2. **Cases vs. Incidence**: Official figures reflect registered police FIRs, not actual societal prevalence. Increased reporting can indicate greater reporting accessibility rather than deteriorating safety.
3. **2023 Reporting Boundary**: NCRB *Crime in India 2023* has released national snapshot totals (`9-2023.pdf`), while detailed State/UT spreadsheets remain unreleased by NCRB; 2022 remains the latest granular state-level edition.

---

## License

This project is open-source under the [MIT License](LICENSE). Official crime data is sourced from public NCRB publications under the Government of India Open Data directives.
