# OCR Recruitment System - Backend API

Backend REST API untuk sistem rekrutmen berbasis OCR: upload CV, ekstraksi teks, parsing data kandidat, dan scoring otomatis berdasarkan job requirements.

Dibangun dengan **FastAPI**, **SQLAlchemy**, dan **Pydantic v2**.

---

## Tech Stack

| Layer            | Teknologi                                    |
|------------------|----------------------------------------------|
| Web Framework    | FastAPI + Uvicorn                            |
| ORM              | SQLAlchemy 2.0                               |
| Validasi Data    | Pydantic v2 + pydantic-settings              |
| Database         | SQLite (dev) / PostgreSQL (production)       |
| OCR              | Tesseract, pdf2image, PyPDF2, python-docx    |
| Testing          | pytest, pytest-asyncio, httpx (TestClient)   |

---

## Prerequisites

- Python **3.9+** (project dikembangkan di 3.12)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) terinstall di sistem (untuk OCR scanned PDF). Set path via `TESSERACT_PATH` di `.env` jika tidak ada di PATH.

---

## Setup

```bash
# 1. Buat virtual environment (sekali saja)
python -m venv .venv

# 2. Aktifkan
#   Windows:
.venv\Scripts\activate
#   Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Opsional) buat konfigurasi dari template
cp .env.example .env
```

Tanpa file `.env`, aplikasi tetap berjalan menggunakan nilai default dari `app/core/config.py` (SQLite, upload ke `./uploads`, dll).

---

## Menjalankan Server

> Wajib dijalankan dari **root project** ini (tempat `.env` dan `./uploads` relatif di-resolve).

### Development (auto-reload)

```bash
uvicorn app.main:app --reload --port 8000
```

atau:

```bash
python app/main.py
```

### Production (Linux)

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000
```

### Verifikasi

- Interactive API docs (Swagger): <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- Health check: <http://127.0.0.1:8000/api/health>

Database SQLite (`ocr_recruitment.db`) dan folder `uploads/` dibuat otomatis saat startup.

---

## Konfigurasi (`.env`)

Variabel utama (lihat `.env.example` untuk lengkap):

| Variable           | Default                 | Keterangan                       |
|--------------------|-------------------------|----------------------------------|
| `DATABASE_URL`     | `sqlite:///./ocr_recruitment.db` | `postgresql://...` untuk produksi |
| `API_STR`          | `/api/`                 | Prefix semua endpoint API        |
| `DEBUG`            | `True`                  | Matikan di produksi              |
| `UPLOAD_DIR`       | `./uploads`             | Lokasi file CV tersimpan         |
| `MAX_FILE_SIZE`    | `10485760` (10MB)       | Maksimal ukuran file             |
| `ALLOWED_FILE_TYPES` | `pdf,docx`            | Tipe file yang diizinkan         |
| `OCR_ENGINE`       | `tesseract`             | `tesseract` / `azure` / `google` |
| `PDF_DPI`          | `300`                   | Resolusi rendering PDF untuk OCR |
| `CORS_ORIGINS`     | `http://localhost:5173,...` | Origin frontend yang diizinkan |

---

## API Endpoints

Semua endpoint (kecuali `/`, `/docs`, `/redoc`, `/debug/config`) berada di bawah prefix `/api`.

### System

| Method | Path         | Deskripsi                     |
|--------|--------------|-------------------------------|
| GET    | `/`          | Info aplikasi                 |
| GET    | `/api/health`| Health check + status database|
| GET    | `/api/stats` | Statistik sistem              |
| GET    | `/debug/config` | Konfigurasi aktif (hanya saat `DEBUG=True`) |

### Upload

| Method | Path                                | Deskripsi                        |
|--------|-------------------------------------|----------------------------------|
| POST   | `/api/upload/cv`                    | Upload 1 file CV (`multipart/form-data`) |
| POST   | `/api/upload/cv-batch`              | Upload banyak file CV sekaligus |
| GET    | `/api/upload/{upload_id}/status`    | Cek status upload               |
| DELETE | `/api/upload/{upload_id}`           | Hapus upload + file di disk     |

Contoh upload 1 file:

```bash
curl -X POST http://127.0.0.1:8000/api/upload/cv \
  -F "file=@cv.pdf" \
  -F "job_requirement_id=<job_id>"
```

### CV Processing

| Method | Path                          | Deskripsi                                  |
|--------|-------------------------------|---------------------------------------------|
| POST   | `/api/cv/{file_id}/process`   | Proses CV (extract + parse) lalu simpan sebagai candidate |
| POST   | `/api/cv/batch/process`       | Proses banyak CV sekaligus (body: `{"file_ids": [...]}`) |
| GET    | `/api/cv/list`                | List candidates (pagination & sorting)      |
| GET    | `/api/cv/{candidate_id}`      | Detail candidate                            |
| DELETE | `/api/cv/{candidate_id}`      | Hapus candidate                             |

Query params `/api/cv/list`: `page` (default 1), `page_size` (default 20, max 100), `sort_by` (`created_at|name|email|experience_years`), `sort_order` (`asc|desc`).

### Job Requirements

| Method | Path              | Deskripsi                         |
|--------|-------------------|-----------------------------------|
| GET    | `/api/jobs`       | List semua job                    |
| POST   | `/api/jobs`       | Buat job baru + scoring criteria  |
| GET    | `/api/jobs/{job_id}` | Detail job + criteria          |
| PUT    | `/api/jobs/{job_id}` | Update job + ganti criteria    |
| DELETE | `/api/jobs/{job_id}` | Hapus job                      |

Contoh body `POST /api/jobs`:

```json
{
  "title": "Backend Engineer",
  "description": "Build REST APIs",
  "criteria": [
    {
      "name": "Python",
      "type": "skill",
      "weight": 1.0,
      "keywords": ["python", "fastapi"]
    },
    {
      "name": "Pengalaman",
      "type": "experience",
      "weight": 1.0,
      "min_value": 2,
      "max_value": 6
    }
  ]
}
```

Tipe criteria: `skill`, `experience`, `education`, `keyword`, `custom`.

### Scoring

| Method | Path                            | Deskripsi                              |
|--------|---------------------------------|----------------------------------------|
| POST   | `/api/score/{candidate_id}`     | Score 1 kandidat utk 1 job (body: `{"job_requirement_id": "..."}`) |
| POST   | `/api/score/batch`              | Score banyak kandidat (body: `{"candidate_ids": [...], "job_requirement_id": "..."}`) |
| GET    | `/api/score/ranked/{job_id}`    | Daftar kandidat terurut by score (params: `limit`, `offset`) |
| GET    | `/api/score/{candidate_id}/details` | Detail skor kandidat (params: `job_id`) |

---

## Alur Penggunaan

1. **Buat job** → `POST /api/jobs` dengan scoring criteria.
2. **Upload CV** → `POST /api/upload/cv` (dapat `upload_id`).
3. **Proses CV** → `POST /api/cv/{file_id}/process` (hasil: `candidate_id`).
4. **Score** → `POST /api/score/{candidate_id}` dengan `job_requirement_id`.
5. **Lihat ranking** → `GET /api/score/ranked/{job_id}`.

---

## Struktur Project

```
.
├── app/
│   ├── main.py                 # Entry point FastAPI (app, CORS, lifespan)
│   ├── api/
│   │   ├── api_router.py       # Agregator semua router
│   │   ├── deps.py             # Dependency (get_db)
│   │   └── routes/             # upload, cv, jobs, scoring, system
│   ├── core/
│   │   └── config.py           # Settings (pydantic-settings)
│   ├── db/
│   │   └── session.py          # Engine, session, init_db
│   ├── models/                 # SQLAlchemy models (per domain)
│   │   ├── base.py             # Declarative Base
│   │   ├── enums.py            # Enum bersama
│   │   ├── upload.py / candidate.py / job.py / score.py
│   ├── schemas/                # Pydantic schemas (per domain)
│   │   ├── common.py / upload.py / cv.py / job.py / scoring.py / system.py
│   └── services/               # Business logic
│       ├── file_storage.py     # Save/validate/delete file
│       ├── ocr.py              # OCR + parsing CV
│       ├── cv.py               # Persistence kandidat
│       └── scoring.py          # Scoring + analytics
├── uploads/                    # File CV tersimpan (runtime)
├── requirements.txt
├── .env.example
└── ocr_recruitment.db          # SQLite (runtime, auto-create)
```

> Catatan: project memakai **namespace packages** (tanpa `__init__.py`). Jalankan semua perintah dari root project.