<div align="center">

# 🧾 Invoice Data Extraction System

### AI-Powered Invoice Intelligence for Indian Pharmaceutical & Hospital Supply Chains

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![AI Model](https://img.shields.io/badge/AI-Qwen%20Vision-blueviolet?style=flat-square)](https://openrouter.ai)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=flat-square)](#license)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=flat-square)](#)
[![Version](https://img.shields.io/badge/Version-2.0-blue?style=flat-square)](#)

**Upload any invoice PDF or image → Get structured JSON in seconds**

*Handles multi-page PDFs · GST validation · Free item splitting · OCR rotation correction · Smart caching*

</div>

---
## 🎥 End-to-End Invoice Processing Demo

This demo showcases the complete workflow of the **Invoice Data Extraction System**, from uploading an invoice to generating validated, structured JSON output. It demonstrates the application's AI-powered extraction pipeline, including document processing, data extraction, financial validation, and the final results presented through the interactive web interface.

**Demo Video:** `Video/demo.mp4`

### Modular Project Architecture

The application is built using a modular Python architecture where each component is responsible for a specific stage of the invoice processing pipeline—from preprocessing and OCR to AI extraction, GST calculation, validation, and caching.

![Project Structure](Screenshots/Screenshot%202026-06-30%20125808.png)

*Core modules include `app_web.py`, `model_client.py`, `preprocessing.py`, `pdf_utils.py`, `gst_calculator.py`, `gst_enrichment.py`, `free_item_splitter.py`, `cache_manager.py`, and `schema.py`, providing a clean and maintainable codebase.*

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [System Architecture](#-system-architecture)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation & Setup](#️-installation--setup)
- [Configuration Reference](#-configuration-reference)
- [Running the Application](#-running-the-application)
- [API Reference](#-api-reference)
- [Extracted JSON Schema](#-extracted-json-schema)
- [Feature Deep Dives](#-feature-deep-dives)
- [Troubleshooting](#-troubleshooting)
- [Production Deployment](#-production-deployment)
- [License](#-license)

---

## 🔍 Overview

Invoice Data Extraction System is a production-ready web application that automates invoice digitization using AI vision models. It is purpose-built for **Indian pharmaceutical and hospital supply chain invoices** — a domain characterized by:

- Multi-page PDFs with continuation rows across pages
- Free/bonus item quantities shown as `"20+2"` in a single cell
- GST breakdowns with CGST + SGST (intra-state) or IGST (inter-state)
- PO numbers buried in remarks, footers, or last pages
- Rotated or low-contrast scanned images

The system converts any such invoice into a clean, validated JSON structure in seconds, replacing hours of manual data entry.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **3-Pass AI Extraction** | Three focused AI calls — header fields, financial totals, line items — for maximum accuracy |
| **Multi-Page PDF Support** | All pages stacked into one image so no field is ever missed, regardless of page location |
| **OCR Rotation Detection** | Detects and corrects 90°/180°/270° rotated scans before extraction |
| **GST Enrichment & Validation** | Fills missing GST fields, validates CGST=SGST rule, handles intra/inter-state logic |
| **Free Item Splitting** | Automatically splits `"20+2"` quantities into separate paid and free records |
| **Smart Caching** | SHA-256 file fingerprint caching — same invoice returns in milliseconds, not seconds |
| **JSON Repair** | Auto-fixes malformed AI responses (missing brackets, trailing commas, unquoted keys) |
| **GSTIN Validation** | 15-character format validation with OCR character correction (`/` → `I`, `0` → `O`) |
| **Image Preprocessing** | CLAHE contrast enhancement, skew correction, orientation fix via OpenCV |
| **5-Tab Web UI** | Summary · Items · Totals · JSON · Validation tabs with download and clipboard support |
| **Duplicate Page Detection** | Identifies and removes ORIGINAL/DUPLICATE/TRIPLICATE copy pages from multi-page PDFs |

---

## 🛠 Tech Stack

| Layer | Technology | Version |
|---|---|---|
| **Web Framework** | Flask + Flask-CORS | 3.0.0 |
| **AI Vision Model** | Qwen Vision (via OpenRouter API) | `qwen/qwen3.7-plus` |
| **OCR** | Baidu Qianfan OCR (via OpenRouter, free tier) | — |
| **PDF Processing** | PyMuPDF (fitz) | 1.24.9 |
| **Image Processing** | OpenCV Headless + Pillow | 4.10.0.84 / 10.4.0 |
| **Numerical** | NumPy + SciPy | 1.26.4 / 1.13.1 |
| **Caching** | File-based SHA-256 JSON cache | — |
| **Frontend** | Vanilla HTML + CSS + JavaScript | (no build step) |
| **Config** | python-dotenv | 1.0.1 |
| **HTTP Client** | Requests | 2.32.3 |

---

## 🏗 System Architecture

```
User Browser
    │
    │  POST /api/extract  (multipart/form-data)
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        app_web.py (Flask)                       │
│                                                                 │
│  1. Receive file + options                                      │
│  2. Generate SHA-256 cache key                                  │
│  3. Check cache → HIT: return instantly | MISS: continue        │
└────────────────────┬────────────────────────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │    pdf_utils.py     │
          │  PDF → PIL Images   │
          │  (PyMuPDF, 150 DPI) │
          └──────────┬──────────┘
                     │ list of PIL images
          ┌──────────▼──────────┐
          │  preprocessing.py   │
          │  • OCR orientation  │◄── ocr_client.py (Qianfan OCR)
          │    detection        │
          │  • Rotation fix     │
          │  • CLAHE contrast   │
          │  • Skew correction  │
          └──────────┬──────────┘
                     │ cleaned images
          ┌──────────▼──────────────────────────────────────────┐
          │                  model_client.py                    │
          │                                                     │
          │  Multi-page: stack all pages → one tall image       │
          │                                                     │
          │  Pass 1 ─── Header fields    (≤500 tokens)          │
          │  Pass 2 ─── Financial totals (≤300 tokens)          │
          │  Pass 3 ─── Line items       (≤4000 tokens)         │
          │                                                     │
          │  → repair_json() → merge 3 results                  │
          └──────────┬──────────────────────────────────────────┘
                     │ raw merged dict
          ┌──────────▼──────────┐    ┌──────────────────────┐
          │  app_web.py         │    │  gst_enrichment.py   │
          │  Type normalization │───►│  Per-item GST derive │
          │  (str→num cleanup)  │    └──────────────────────┘
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │ free_item_splitter  │
          │ "20+2" → 2 records  │
          │ total_quantity calc  │
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │  gst_calculator.py  │
          │  GST validation     │
          │  CGST=SGST check    │
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │  cache_manager.py   │
          │  Save result as     │
          │  {hash}.json        │
          └──────────┬──────────┘
                     │
                     ▼
              JSON Response
          { success, data, metadata, reasoning }
```

---

## 📁 Project Structure

```
invoice_extractorv1.0/
│
├── README.md                        ← You are here
├── Screenshots/                     ← UI screenshots
│   ├── Screenshot 2026-06-30 *.png
│   └── ...
│
└── invoice-extractor/               ← Main application
    │
    ├── app_web.py                   ← Flask server, extraction pipeline, API endpoints
    ├── schema.py                    ← AI prompts (system + user + 3 focused sub-prompts)
    ├── model_client.py              ← OpenRouter API client, 3-pass extraction, JSON repair
    ├── ocr_client.py                ← Qianfan OCR for rotation detection
    ├── pdf_utils.py                 ← PDF → PIL image conversion (PyMuPDF)
    ├── preprocessing.py             ← Image pipeline: rotate, deskew, contrast, denoise
    ├── cache_manager.py             ← SHA-256 file cache (JSON files, TTL-based)
    ├── free_item_splitter.py        ← Splits "20+2" quantities into paid/free records
    ├── gst_calculator.py            ← GST validation, CGST=SGST rule, transaction type
    ├── gst_enrichment.py            ← Per-item GST derivation when columns are missing
    │
    ├── templates/
    │   └── index.html               ← Complete web UI (HTML + CSS + JS, single file)
    │
    ├── uploads/                     ← Temporary upload storage
    │   └── .cache/                  ← Cached extraction results ({hash}.json files)
    │
    ├── .env                         ← Your secrets (API key) — never commit this
    ├── .env.example                 ← Config template — safe to share
    ├── requirements.txt             ← Python dependencies (pinned versions)
    ├── start.bat                    ← One-click Windows startup script
    └── .gitignore                   ← Excludes .env, uploads/, __pycache__/
```

---

## 📦 Prerequisites

Before installing, make sure you have the following:

### 1. Python 3.11+
Download from [python.org](https://www.python.org/downloads/). Verify your install:
```bash
python --version
# Python 3.11.x or higher
```

### 2. Poppler (required for PDF processing)
PyMuPDF handles PDF rendering — **no separate Poppler install needed** for most setups. If you encounter PDF errors, install Poppler manually:

| OS | Command |
|---|---|
| **Windows** | Download from [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases), extract and add `bin/` to your `PATH` |
| **macOS** | `brew install poppler` |
| **Ubuntu/Debian** | `sudo apt-get install poppler-utils` |
| **RHEL/CentOS** | `sudo yum install poppler-utils` |

### 3. OpenRouter API Key
This system uses [OpenRouter](https://openrouter.ai) to access the Qwen Vision AI model.

1. Create a free account at [openrouter.ai](https://openrouter.ai)
2. Go to **Keys** → **Create Key**
3. Copy the key — it starts with `sk-or-`
4. Add credits to your account (Qwen models are very affordable — typical invoice costs ~$0.001)

---

## ⚙️ Installation & Setup

### Step 1 — Clone or Download the Repository

```bash
git clone https://github.com/your-org/invoice-extractor.git
cd invoice-extractor/invoice-extractor
```

Or download the ZIP and extract it.

---

### Step 2 — Create a Virtual Environment (Recommended)

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

---

### Step 3 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs all pinned dependencies:

| Package | Version | Purpose |
|---|---|---|
| `Flask` | 3.0.0 | Web framework |
| `Pillow` | 10.4.0 | Image handling (PIL) |
| `opencv-python-headless` | 4.10.0.84 | Rotation, contrast, deskew |
| `numpy` | 1.26.4 | Image array operations |
| `scipy` | 1.13.1 | Scientific image analysis |
| `pymupdf` | 1.24.9 | PDF → image conversion |
| `imagehash` | 4.3.1 | Perceptual image hashing |
| `requests` | 2.32.3 | HTTP calls to OpenRouter |
| `python-dotenv` | 1.0.1 | Load `.env` config file |

---

### Step 4 — Configure Environment Variables

Copy the example config:
```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` in any text editor and fill in your values:

```env
# ── REQUIRED ────────────────────────────────────────
OPENROUTER_API_KEY=sk-or-your-key-here

# ── MODEL (optional, default shown) ─────────────────
MODEL_NAME=qwen/qwen3.7-plus

# ── APPLICATION ──────────────────────────────────────
RENDER_DPI=150
MAX_FILE_SIZE_MB=20

# ── CACHING ──────────────────────────────────────────
CACHE_ENABLED=true
CACHE_DIRECTORY=uploads/.cache
CACHE_MAX_AGE_HOURS=24

# ── PDF ──────────────────────────────────────────────
MAX_PDF_PAGES=20
```

> ⚠️ **Never commit `.env` to version control.** It is already listed in `.gitignore`.

---

## 🚀 Running the Application

### Option A — Windows One-Click Start

Double-click `start.bat` in the `invoice-extractor/` directory.

This opens a terminal, starts Flask on port `8000`, and prints the server URL.

---

### Option B — Manual Start

```bash
# Make sure your virtual environment is active
python app_web.py
```

Server starts at:
```
http://localhost:8000
```

---

### Option C — Expose Publicly via Ngrok (Optional)

To share the app with others or test from a different device:

1. Install [ngrok](https://ngrok.com/download)
2. Start the Flask server (Step A or B above)
3. In a **new terminal**, run:
   ```bash
   ngrok http 8000
   ```
4. Copy the `https://xxxx.ngrok.io` URL — share it with anyone

---

### Verifying the Server is Running

Open your browser and navigate to:
```
http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "api_configured": true
}
```

If `api_configured` is `false`, your `OPENROUTER_API_KEY` in `.env` is missing or invalid.

---

## 🔧 Configuration Reference

All configuration is managed via the `.env` file.

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | *(required)* | Your OpenRouter API key (`sk-or-...`) |
| `MODEL_NAME` | `qwen/qwen3.7-plus` | AI model to use for extraction |
| `RENDER_DPI` | `150` | DPI resolution for PDF-to-image conversion |
| `MAX_FILE_SIZE_MB` | `20` | Maximum upload file size in megabytes |
| `CACHE_ENABLED` | `true` | Enable/disable result caching |
| `CACHE_DIRECTORY` | `uploads/.cache` | Directory to store cached JSON results |
| `CACHE_MAX_AGE_HOURS` | `24` | How long before a cache entry expires |
| `MAX_PDF_PAGES` | `20` | Maximum number of PDF pages to process |

### Choosing a Model

The system is designed for vision models. Recommended options via OpenRouter:

| Model | Speed | Accuracy | Cost |
|---|---|---|---|
| `qwen/qwen3.7-plus` | Fast | Very High | Low |
| `qwen/qwen2.5-vl-72b-instruct` | Medium | Highest | Medium |
| `openai/gpt-4o` | Fast | High | High |

---

## 📡 API Reference

### `POST /api/extract`

Extract structured data from an invoice file.

**Request** — `multipart/form-data`

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `file` | File | ✅ | — | Invoice file (PDF, PNG, JPG, TIFF, BMP, WebP) |
| `use_ocr` | string | ❌ | `"false"` | `"true"` to enable OCR-based rotation detection |
| `two_pass` | string | ❌ | `"true"` | `"true"` to use 3-pass extraction (recommended) |
| `multi_page` | string | ❌ | `"true"` | `"true"` to process all pages of a PDF |
| `use_cache` | string | ❌ | `"true"` | `"true"` to return cached result if available |

**Example cURL request:**
```bash
curl -X POST http://localhost:8000/api/extract \
  -F "file=@invoice.pdf" \
  -F "use_ocr=true" \
  -F "two_pass=true" \
  -F "multi_page=true" \
  -F "use_cache=true"
```

**Success Response — `200 OK`**
```json
{
  "success": true,
  "data": {
    "invoice_id": null,
    "invoice_number": "INV-2026-001",
    "invoice_date": "15/06/2026",
    "customer_name": "DEENANATH MANGESHKAR HOSPITAL",
    "customer_gstin": "27AIWPA8054A1ZA",
    "seller_name": "MEHTA PHARMA PVT LTD",
    "seller_gstin": "27AAAFM1944N1ZN",
    "currency_code": "INR",
    "PO_number": "DMH/PO/PHRMCY/2026-27/3906",
    "invoice_amount": 15420.50,
    "total_gst_amount": 1650.00,
    "items": [ ... ]
  },
  "metadata": {
    "processing_time": 4.21,
    "page_count": 2,
    "extraction_mode": "multi-page (2 pages, two-pass)",
    "cached": false
  },
  "reasoning": [
    "[14:22:01] File received, analyzing (two-pass, multi-page)...",
    "[14:22:01] PDF detected, converting to images...",
    "[14:22:02] Multi-page mode: Processing all 2 pages",
    "[14:22:06] ✅ GST validation passed (intra-state)"
  ]
}
```

**Error Response — `400 / 500`**
```json
{
  "error": "API key not configured. Please set OPENROUTER_API_KEY in .env file."
}
```

---

### `GET /api/health`

Check server and API configuration status.

```bash
curl http://localhost:8000/api/health
```

```json
{
  "status": "healthy",
  "api_configured": true
}
```

---

### `GET /api/cache/stats`

View cache statistics.

```json
{
  "total_entries": 12,
  "total_size_mb": 0.43,
  "oldest_entry_hours": 3.2
}
```

---

### Supported File Formats

| Format | Extension | Notes |
|---|---|---|
| PDF | `.pdf` | Single or multi-page, up to 20 pages |
| JPEG | `.jpg`, `.jpeg` | Standard camera/scanner output |
| PNG | `.png` | Lossless, good for screenshots |
| TIFF | `.tiff`, `.tif` | Common scanner format |
| BMP | `.bmp` | Uncompressed bitmap |
| WebP | `.webp` | Modern web format |

**Maximum file size:** 20 MB (configurable via `MAX_FILE_SIZE_MB`)

---

## 📊 Extracted JSON Schema

The system returns a single JSON object per invoice. Fields follow this exact order:

### Header Fields

| Field | Type | Example | Description |
|---|---|---|---|
| `invoice_id` | null | `null` | Reserved — populated by downstream systems |
| `invoice_number` | string | `"INV-2026-001"` | Invoice number as printed |
| `invoice_date` | string | `"15/06/2026"` | Invoice issue date (DD/MM/YYYY) |
| `due_date` | string\|null | `"30/06/2026"` | Payment due date |
| `customer_name` | string | `"DMH HOSPITAL"` | Buyer organization name only |
| `customer_gstin` | string\|null | `"27AIWPA8054A1ZA"` | 15-char buyer GSTIN |
| `seller_name` | string | `"MEHTA PHARMA"` | Seller organization name only |
| `seller_gstin` | string\|null | `"27AAAFM1944N1ZN"` | 15-char seller GSTIN |
| `currency_code` | string | `"INR"` | Always `"INR"` for Indian invoices |
| `PO_number` | string\|null | `"DMH/PO/PHRMCY/2026-27/3906"` | Purchase order reference |
| `DC_date` | string\|null | `null` | Delivery challan date |
| `DC_number` | string\|null | `null` | Delivery challan number |

### Financial Totals

| Field | Type | Example | Description |
|---|---|---|---|
| `invoice_amount` | number | `15420.50` | Final payable amount |
| `round_off` | number\|null | `-0.50` | Round-off adjustment (can be negative) |
| `total_gst_rate` | number\|null | `12` | Combined GST % (CGST% + SGST%) |
| `total_quantity` | number | `150` | Sum of paid item quantities only |
| `total_cgst_rate` | number\|null | `6` | CGST rate % |
| `total_cgst_amount` | number\|null | `825.00` | Total CGST amount |
| `total_sgst_rate` | number\|null | `6` | SGST rate % |
| `total_sgst_amount` | number\|null | `825.00` | Total SGST amount |
| `total_igst_rate` | number\|null | `null` | IGST rate % (null if intra-state) |
| `total_igst_amount` | number | `0` | IGST amount (0 if intra-state) |
| `total_gst_amount` | number\|null | `1650.00` | Total GST = CGST + SGST + IGST |

### Line Item Fields (per item in `items[]`)

| Field | Type | Example | Description |
|---|---|---|---|
| `description` | string | `"PARACETAMOL 500MG"` | Product name |
| `Pack` | string\|null | `"10TAB"` | Pack size / UOM |
| `Batch` | string\|null | `"AB1234"` | Batch number |
| `quantity` | number | `20` | Quantity (number after free item split) |
| `free_item_yn` | string | `"0"` | `"0"` = paid, `"1"` = free/bonus |
| `unit_price` | number\|null | `48.71` | Per-unit selling price |
| `total_price` | number\|null | `974.20` | Total billed amount for this row |
| `reference_number` | string\|null | `null` | Part/reference number |
| `hsn_sac` | string\|null | `"30049099"` | 8-digit HSN code |
| `item_code` | string\|null | `"SR-02-0391"` | Internal item/rack code |
| `expiry_date` | string\|null | `"30/11/2027"` | Expiry date (DD/MM/YYYY) |
| `Discount` | number\|null | `5.0` | Discount value |
| `Discount_type` | string\|null | `"percent"` | `"percent"` or `"amount"` |
| `Value` | number\|null | `925.49` | Pre-GST value (if column exists) |
| `Gst%` | number\|null | `12` | GST rate for this item |
| `MRP` | number\|null | `60.00` | Maximum retail price |
| `cgst_rate` | number\|null | `6` | Item-level CGST % |
| `cgst_amount` | number\|null | `55.53` | Item-level CGST amount |
| `sgst_rate` | number\|null | `6` | Item-level SGST % |
| `sgst_amount` | number\|null | `55.53` | Item-level SGST amount |
| `igst_rate` | number\|null | `null` | Item-level IGST % |
| `igst_amount` | number\|null | `null` | Item-level IGST amount |
| `GST_AMT` | number\|null | `111.06` | Total GST for this item |
| `taxable_value` | number\|null | `925.49` | Taxable amount (after discount, before GST) |

---

## 🔬 Feature Deep Dives

### 1. 3-Pass Extraction Strategy

Rather than asking the AI to extract everything in a single prompt, the system makes **three focused API calls** per invoice. Each pass has a narrow token budget and a single responsibility:

```
Pass 1 — Header Fields  (≤ 500 tokens)
  invoice_number, invoice_date, customer_name, seller_name,
  customer_gstin, seller_gstin, PO_number, DC_number, DC_date

Pass 2 — Financial Totals  (≤ 300 tokens)
  invoice_amount, taxable_amount, total_gst_amount,
  total_cgst_rate, total_cgst_amount, total_sgst_rate,
  total_sgst_amount, round_off, total_quantity

Pass 3 — Line Items  (≤ 4000 tokens)
  Full items[] array with all per-item fields
```

**Why this works:** Narrow focus reduces hallucination and increases field-level accuracy. If one pass fails, the partial results from the other two passes are still preserved.

---

### 2. Page-Agnostic Multi-Page Extraction

**Old approach (wrong):** Process page 1 for header, pages 2–N for items only.
This misses PO numbers hidden in remarks on page 2, or totals on the last page.

**New approach (correct):** Stack ALL pages vertically into one tall image. Send the complete document to each of the 3 passes.

```
Page 1  ┐
Page 2  ├── Stacked vertically → single tall image → all 3 passes see everything
Page 3  ┘
```

Result: Fields like PO numbers in footers, totals on last pages, and items that span multiple pages are never missed.

---

### 3. Free Item Handling

Pharmaceutical invoices frequently bundle free/bonus units: *"Buy 20, get 2 free"*, shown as `"20+2"` in a single cell.

The system handles three input patterns:

| Pattern | Input | Output |
|---|---|---|
| Combined string | `quantity: "20+2"` | Two records |
| Separate fields | `quantity: 20, free_quantity: 2` | Two records |
| Plain quantity | `quantity: 20` | One record, `free_item_yn: "0"` added |

For each split, the free record gets **proportionally recalculated monetary values**:

```
Paid record:  quantity=20, free_item_yn="0"
              unit_price=48.71, total_price=974.20 (unchanged)

Free record:  quantity=2, free_item_yn="1"
              total_price = 974.20 × (2/20) = 97.42
              GST_AMT, cgst_amount, sgst_amount → proportional
```

`total_quantity` in the invoice header counts **only paid items** (`free_item_yn = "0"`).

---

### 4. Smart Caching

Every extraction result is cached using a SHA-256 fingerprint of `file_bytes + options`:

```python
cache_key = sha256(file_bytes + json(use_ocr, two_pass, multi_page))
```

- Same file + same options = same hash = instant cache hit
- Different file OR different options = different hash = fresh extraction
- Cache entries expire after `CACHE_MAX_AGE_HOURS` (default 24h)
- Cache shown in UI as `⚡ Cached Result` status badge

---

### 5. Image Preprocessing Pipeline

Every image passes through this pipeline before reaching the AI:

```
Step 1: Orientation Detection
  → Qianfan OCR model asked: "Is this rotated 0°/90°/180°/270°?"
  → Fallback: heuristic ink density (invoice headers have more ink at top)

Step 2: Rotation Correction
  → OpenCV warpAffine to correct detected rotation

Step 3: Contrast Enhancement
  → CLAHE (Contrast Limited Adaptive Histogram Equalization)
  → Makes faded text on old or low-quality scans clearly readable

Step 4: Skew Correction (optional)
  → Hough line detection to fix slightly tilted scans

Step 5: Denoising / Sharpening (optional, disabled by default)
  → Gaussian smoothing or Unsharp Mask sharpening
```

Orientation detection only runs on page 1 for multi-page PDFs to minimize API calls.

---

### 6. GSTIN Validation

Every extracted GSTIN is validated against the Indian GST format:

```
Format: [2 digits][10 alphanumeric][1 digit][1 alpha][1 alphanumeric]
Example: 27AIWPA8054A1ZA  (15 characters total)
```

If the extracted value has ≠ 15 characters, OCR corrections are applied:
- `/` → `I`
- `1` (digit one) → `I`  
- `0` (digit zero) → `O`

If still invalid after corrections → field set to `null`.

---

## 🐛 Troubleshooting

### PDF conversion fails

**Symptom:** `Failed to convert PDF to images` or `PDF has 0 pages`

**Fix:**
1. Verify the PDF is not password-protected
2. Try opening the PDF in a viewer first — confirm it's not corrupted
3. If using scanned PDFs, ensure the file is a valid PDF (not renamed from another format)
4. Install/reinstall PyMuPDF: `pip install --force-reinstall pymupdf==1.24.9`

---

### API key errors

**Symptom:** `API key not configured` or `401 Unauthorized`

**Fix:**
1. Open `.env` — confirm `OPENROUTER_API_KEY=sk-or-xxxxx` is set
2. No spaces around the `=` sign
3. The key must start with `sk-or-`
4. Verify the key is active at [openrouter.ai/keys](https://openrouter.ai/keys)
5. Check you have credits at [openrouter.ai/credits](https://openrouter.ai/credits)

---

### Poor extraction accuracy

**Symptom:** Fields are null, wrong values, or items are missing

**Fixes to try (in order):**
1. Enable OCR in the UI checkbox — helps with rotated or low-contrast scans
2. Ensure `two_pass=true` (enabled by default in UI)
3. Ensure `multi_page=true` for multi-page PDFs (enabled by default)
4. Try a higher DPI: set `RENDER_DPI=200` in `.env`
5. If the invoice is a low-res scan, try scanning at 300+ DPI before uploading

---

### Extraction is slow

**Symptom:** Takes more than 15 seconds per invoice

**Fix:**
1. Enable caching (checkbox in UI) — subsequent uploads of same invoice are instant
2. Check your network connection to OpenRouter API
3. Try a faster model — `qwen/qwen3.7-plus` is generally faster than larger variants
4. For large multi-page PDFs, reduce `MAX_PDF_PAGES` in `.env`

---

### Cache not working

**Symptom:** Same invoice is re-processed every time despite cache being enabled

**Fix:**
1. Confirm `CACHE_ENABLED=true` in `.env`
2. Check the `uploads/.cache/` folder exists and has write permissions
3. Verify the "Cache previous results" checkbox is checked in the UI
4. If files differ even slightly (different scan, compression), the hash will differ

---

### Server doesn't start

**Symptom:** `python app_web.py` exits with errors

**Common causes:**

| Error | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'flask'` | Run `pip install -r requirements.txt` |
| `Address already in use` (port 8000) | Kill the other process using port 8000, or change the port in `app_web.py` |
| `No module named 'cv2'` | Run `pip install opencv-python-headless==4.10.0.84` |
| `.env file not found` | Copy `.env.example` to `.env` and fill in your API key |

---

## 🚢 Production Deployment

### Security Checklist

Before going to production:

- [ ] Set a strong, unique `OPENROUTER_API_KEY`
- [ ] Restrict CORS to specific origins in `app_web.py` (replace `CORS(app)` with `CORS(app, origins=["https://yourdomain.com"])`)
- [ ] Set `CACHE_MAX_AGE_HOURS` appropriately for your data retention policy
- [ ] Enable HTTPS (use a reverse proxy like Nginx or run behind a load balancer)
- [ ] Add authentication if the API is publicly accessible
- [ ] Set `MAX_FILE_SIZE_MB` to a reasonable limit for your use case
- [ ] Restrict `MAX_PDF_PAGES` to prevent abuse

### Running with Gunicorn (Linux/macOS)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app_web:app
```

### Running with Waitress (Windows)

```bash
pip install waitress
waitress-serve --host=0.0.0.0 --port=8000 app_web:app
```

### Nginx Reverse Proxy Config (Example)

```nginx
server {
    listen 80;
    server_name invoice.yourdomain.com;

    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }
}
```

### Environment Variables for Production

```env
OPENROUTER_API_KEY=sk-or-your-production-key
MODEL_NAME=qwen/qwen2.5-vl-72b-instruct
CACHE_ENABLED=true
CACHE_MAX_AGE_HOURS=48
MAX_PDF_PAGES=10
MAX_FILE_SIZE_MB=15
```

### Monitoring

- Monitor logs for extraction errors and API timeouts
- Track OpenRouter API usage and costs at [openrouter.ai/activity](https://openrouter.ai/activity)
- Watch the `uploads/.cache/` folder size and run `GET /api/cache/stats` periodically
- Set up alerts for `500` errors on the `/api/extract` endpoint

---

## 📝 License

This project is **proprietary software**. All rights reserved.

Unauthorized copying, distribution, modification, or use of this software, in whole or in part, without explicit written permission from the owner is strictly prohibited.

---

## 📞 Support

For issues, bugs, or feature requests — contact the development team or open an issue in the project repository.

---

<div align="center">

**Version 2.0** &nbsp;·&nbsp; **Last Updated: June 2026** &nbsp;·&nbsp; **Status: Production Ready**

*Built for Indian pharmaceutical & hospital invoice digitization*

</div>
