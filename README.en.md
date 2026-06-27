# WB Margin Analyzer

> **AI-powered margin analytics tool for Wildberries marketplace sellers**

Russian e-commerce sellers on Wildberries face a real challenge: the platform charges a 15–25% commission, plus two-way logistics fees, plus return logistics at 1.5× the base rate. A product that looks profitable at first glance can easily be running at a loss. This tool makes the invisible visible — upload two Excel files, get a complete margin breakdown with AI-generated recommendations in seconds.

**🌐 Live demo:** [wb.tinacodes.space](https://wb.tinacodes.space) — `demo@demo.com` / `demo1234`

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Sonnet_4.6-CC785C?logo=anthropic&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-60_tests-0A9EDC?logo=pytest&logoColor=white)

---

## The Problem It Solves

A Wildberries seller with 200+ SKUs has no easy way to see which products are profitable and which are quietly draining their budget. The platform's fee structure — commission + outbound logistics + return logistics (at 1.5× rate) — makes manual calculations error-prone and time-consuming.

**Before:** a spreadsheet with 200 rows and no clear picture.

**After:** upload two files → color-coded margin table → AI diagnosis with specific price recommendations → exportable Excel report — all in under 30 seconds.

---

## Screenshots

### File Upload
![Upload](docs/screenshots/1%20upload.PNG)

### Margin Dashboard — color-coded table with filters
![Dashboard](docs/screenshots/2%20dashboard.PNG)

### Product Detail Modal
![Product Card](docs/screenshots/3%20modalwindow%20wb%20card%20item.PNG)

### What If Price Simulator
![What If](docs/screenshots/4%20what%20if.PNG)

### Claude AI Interpretation
![AI Interpretation](docs/screenshots/5%20AI-%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D0%BF%D1%80%D0%B5%D1%82%D0%B0%D1%86%D0%B8%D1%8F.PNG)

### AI Chat — context-aware Q&A
![AI Chat](docs/screenshots/6%20ai%20chat.PNG)

### Excel Export with color-coded rows
![Excel](docs/screenshots/7-1%20exel.PNG)

### Analysis History
![History](docs/screenshots/8%20history.PNG)

---

## Quick Start

```bash
git clone https://github.com/TinaUma/wb-margin-analyzer.git
cd wb-margin-analyzer
cp .env.example .env          # add SECRET_KEY and ANTHROPIC_API_KEY
docker compose up --build
```

- App → **http://localhost:5173**
- API Docs → **http://localhost:8000/docs**

> `ANTHROPIC_API_KEY` is optional — the app starts without it; AI endpoints return `503` with a clear message.
> **Live demo:** AI features are disabled (Anthropic API blocks RU server IPs). Screenshots of working AI are in the section above.

---

## How It Works

```
User uploads 2 .xlsx files (purchases + sales)
       ↓
FastAPI validates column structure (openpyxl)
       ↓
BackgroundTask: pandas calculates margin per SKU
  margin = (revenue − commission − logistics − purchase cost) / revenue × 100%
  return logistics = 1.5 × base rate (Wildberries tariff)
       ↓
Results stored in PostgreSQL
       ↓
Frontend polls status every 2s → renders table
       ↓
Claude Sonnet 4.6 generates: Diagnosis / Recommendations / Risks
       ↓
User downloads .xlsx with color-coded rows and AI interpretation sheet
```

---

## Features

| Feature | Details |
|---|---|
| **Color-coded table** | Green ≥25% / Yellow 10–25% / Red <10% margin |
| **Zone filter** | Filter buttons with per-zone product counts |
| **Column sorting** | Click header to sort by margin, profit, or price |
| **Product detail modal** | Full metrics for any SKU on row click |
| **What If simulator** | Price/cost sliders — real-time margin recalculation, zero API calls |
| **AI interpretation** | Claude generates diagnosis with tables and specific numbers |
| **AI chat** | Context-aware Q&A with sliding 5-message window |
| **Excel export** | Color-coded rows + AI interpretation on Sheet 2 |
| **Analysis history** | All past analyses with date and status |
| **Async processing** | Upload returns 202 instantly; analysis runs in background |

---

## Tech Stack

### Backend
- **FastAPI** (async) + **SQLAlchemy 2.0** async ORM
- **Alembic** migrations (auto-run on container start)
- **pandas** for Excel parsing and margin calculations
- **openpyxl** for file validation and color-coded Excel export
- **anthropic** Python SDK — `AsyncAnthropic`, `claude-sonnet-4-6`
- **python-jose** + **bcrypt** for JWT auth

### Frontend
- **React 18** + **TypeScript** + **Vite**
- **Tailwind CSS v3**
- **React Router v6**
- **Axios** with interceptors (auto-attach Bearer token, redirect on 401)

### Infrastructure
- **PostgreSQL 16** with named volume
- **Docker Compose** — single-command startup
- **Nginx** — serves React SPA, proxies `/api` to FastAPI

---

## Testing

```bash
pytest -v   # 60 tests
```

Coverage: file validator, margin analytics engine, all API endpoints (upload, analyses, AI, export), JWT auth boundaries.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL async URL (`postgresql+asyncpg://...`) |
| `SECRET_KEY` | ✅ | JWT signing secret (`openssl rand -hex 32`) |
| `ANTHROPIC_API_KEY` | ☑ optional | Claude API key — app runs without it |
| `CORS_ORIGINS` | ☑ optional | JSON list of allowed origins |

---

## Project Documentation

- [Technical Specification (PDF, Russian)](docs/WB%20Margin%20Analyzer%20—%20ТЗ%20v2.0.pdf) — full product requirements doc
- [Interactive API Docs](http://localhost:8000/docs) — Swagger UI

---

## Project Structure

```
wb-margin-analyzer/
├── backend/
│   ├── api/v1/          # FastAPI routers (auth, uploads, analyses)
│   ├── core/            # Config (pydantic-settings)
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic request/response schemas
│   └── services/        # Business logic (analysis, AI, export, validator)
├── frontend/
│   └── src/
│       ├── api/         # Axios client + typed API functions
│       ├── components/  # MarginTable, WhatIfPanel, ChatBlock, FileDropzone
│       ├── context/     # AuthContext (JWT)
│       └── pages/       # Login, Register, Upload, Dashboard, History
├── tests/               # pytest — 60 tests
├── docs/                # Screenshots + technical specification
├── alembic/             # DB migrations
└── docker-compose.yml
```
